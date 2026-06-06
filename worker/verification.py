"""Verify extracted facts are grounded in the source PDF via SourceRef quotes."""

import io
import re
from difflib import SequenceMatcher

from pydantic import BaseModel
from pypdf import PdfReader

from schemas.common import SourceRef


class GroundingResult(BaseModel):
    field: str  # dotted path, e.g. "diagnoses[0].source"
    page: int
    grounded: bool
    confidence: float


def extract_page_texts(pdf_bytes: bytes) -> list[str]:
    """Return the text of each page, 0-indexed (page N -> index N-1)."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return [page.extract_text() or "" for page in reader.pages]


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


# Splits a multi-field quote into its individual facts. Quotes commonly stitch
# together several "Key.path: value" fields that live in different spots on the
# page, so we verify each field on its own rather than as one contiguous block.
# Splits on line breaks, semicolons, and before each dotted "Key.path:" label.
_FIELD_BOUNDARY = re.compile(r"[\n\r;]+|(?=[A-Za-z][\w]*(?:\.[\w ]+)+\s*(?:\([^)]*\))?\s*:)")


def _segments(quote: str) -> list[str]:
    """Break a quote into normalized fact segments, dropping trivial fragments."""
    segments = (_normalize(s) for s in _FIELD_BOUNDARY.split(quote))
    return [s for s in segments if len(s) >= 4]


def _segment_found(segment: str, page_text: str, threshold: float) -> bool:
    if segment in page_text:
        return True
    match = SequenceMatcher(None, segment, page_text).find_longest_match(
        0, len(segment), 0, len(page_text)
    )
    return (match.size / len(segment)) >= threshold


def _grounds(
    quote: str,
    page_text: str,
    threshold: float = 0.85,
    coverage: float = 0.6,
) -> bool:
    """True if enough of `quote`'s fields appear (exactly or near-exactly) in `page_text`.

    `threshold` is per-segment string similarity; `coverage` is the fraction of
    segments that must be found for the whole quote to count as grounded.
    """
    q = _normalize(quote)
    t = _normalize(page_text)
    if not q or not t:
        return False
    if q in t:  # fast path: whole quote is one contiguous block
        return True
    segments = _segments(quote)
    if not segments:
        return False
    found = sum(_segment_found(s, t, threshold) for s in segments)
    return (found / len(segments)) >= coverage


def _collect_sources(obj: object, path: str = "") -> list[tuple[str, SourceRef]]:
    """Walk a PatientChart and yield (dotted_path, SourceRef) for every source."""
    if isinstance(obj, SourceRef):
        return [(path, obj)]
    if isinstance(obj, BaseModel):
        found: list[tuple[str, SourceRef]] = []
        for name, value in obj:
            found += _collect_sources(value, f"{path}.{name}" if path else name)
        return found
    if isinstance(obj, list):
        found = []
        for i, item in enumerate(obj):
            found += _collect_sources(item, f"{path}[{i}]")
        return found
    if isinstance(obj, dict):
        found = []
        for key, value in obj.items():
            found += _collect_sources(value, f"{path}.{key}")
        return found
    return []


def verify_chart(
    chart: BaseModel,
    page_texts: list[str],
    threshold: float = 0.85,
) -> list[GroundingResult]:
    """Check every SourceRef quote against the text of the page it cites."""
    results: list[GroundingResult] = []
    for path, ref in _collect_sources(chart):
        idx = ref.page - 1
        page_text = page_texts[idx] if 0 <= idx < len(page_texts) else ""
        results.append(
            GroundingResult(
                field=path,
                page=ref.page,
                grounded=_grounds(ref.quote, page_text, threshold),
                confidence=ref.confidence,
            )
        )
    return results
