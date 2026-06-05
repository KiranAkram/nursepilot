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


def _grounds(quote: str, page_text: str, threshold: float = 0.85) -> bool:
    """True if `quote` appears (exactly or near-exactly) in `page_text`."""
    q = _normalize(quote)
    t = _normalize(page_text)
    if not q:
        return False
    if q in t:
        return True
    match = SequenceMatcher(None, q, t).find_longest_match(0, len(q), 0, len(t))
    return (match.size / len(q)) >= threshold


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
