"""Gemini-backed extraction: SNF referral PDF -> PatientChart."""

import copy
import json
import time

from google import genai
from google.genai import errors, types
from pydantic import ValidationError

from config import GEMINI_API_KEY, GEMINI_MODEL
from schemas import PatientChart

# Cap salvage rounds so a pathological response can't loop forever.
_MAX_SALVAGE_ROUNDS = 50

# Gemini returns 503 (overloaded) / 429 (rate limit) transiently; the SDK does
# not retry them. Back off and retry: 2s, 4s, 8s, 16s.
_RETRYABLE_CODES = {429, 500, 502, 503, 504}
_MAX_ATTEMPTS = 5


def _generate_with_retry(client: genai.Client, **kwargs):
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            return client.models.generate_content(**kwargs)
        except errors.APIError as exc:
            if exc.code not in _RETRYABLE_CODES or attempt == _MAX_ATTEMPTS:
                raise
            time.sleep(2**attempt)

# PatientChart is too large/deep for Gemini's response_schema (constrained
# decoding caps out: "too many states for serving"). Instead we put the schema
# in the prompt, ask for JSON, and enforce the contract with Pydantic on return.
_SCHEMA_JSON = json.dumps(PatientChart.model_json_schema())

EXTRACTION_PROMPT = f"""You are a clinical data extractor for skilled nursing facility (SNF) referrals.

Extract a PatientChart from the attached hospital discharge packet (PDF) and return
ONLY a JSON object matching this JSON Schema (no markdown, no commentary):

{_SCHEMA_JSON}

Rules:
- Use only what is present in the document. Do not invent or infer values that are not written.
- For every field that carries a `source`, fill it with:
  - `page`: the 1-indexed PDF page the fact appears on,
  - `quote`: the verbatim text from that page supporting the fact,
  - `confidence`: 0.0-1.0, your confidence the extraction matches the source.
- Omit optional fields (or use null) when the document does not state them.
- Preserve original units, codes, and wording (ICD-10 codes, doses, ranges) exactly as written.
- `gg_codes` is an object mapping each GG code to its value, e.g. {{"GG0130A": "04"}}.
"""


def _drop_leaf(data: object, loc: tuple) -> bool:
    """Remove the value at a Pydantic error `loc` path. Returns True if removed.

    We delete the offending key/element so the field falls back to its default
    (or None) on re-validation; a list-item error drops that element. If a
    *required* field is what's bad, deletion turns it into a "field required"
    error at the same loc, which the caller skips — so unsalvageable charts still
    raise. Returns False if the path can't be walked.
    """
    parent = data
    for key in loc[:-1]:
        try:
            parent = parent[key]
        except (KeyError, IndexError, TypeError):
            return False
    last = loc[-1]
    if isinstance(last, int) and isinstance(parent, list) and 0 <= last < len(parent):
        del parent[last]
        return True
    if isinstance(parent, dict) and last in parent:
        del parent[last]
        return True
    return False


def validate_with_salvage(raw: dict) -> tuple[PatientChart, list[dict]]:
    """Validate a chart, quarantining individually-bad values instead of failing.

    One bad value (e.g. an out-of-range enum) would otherwise reject the entire
    chart and waste the extraction. Here, each recoverable bad leaf is dropped and
    recorded in `flagged` (path, value, reason) for nurse review; the rest of the
    chart still validates. Errors that can't be salvaged (bad/missing *required*
    fields) still raise.
    """
    data = copy.deepcopy(raw)
    flagged: list[dict] = []
    salvaged: set[tuple] = set()
    for _ in range(_MAX_SALVAGE_ROUNDS):
        try:
            return PatientChart.model_validate(data), flagged
        except ValidationError as exc:
            error = next(
                (e for e in exc.errors() if e["loc"] not in salvaged), None
            )
            if error is None or not _drop_leaf(data, error["loc"]):
                raise
            salvaged.add(error["loc"])
            flagged.append(
                {
                    "path": ".".join(str(p) for p in error["loc"]),
                    "value": error.get("input"),
                    "reason": error.get("msg"),
                }
            )
    return PatientChart.model_validate(data), flagged


def extract_chart_from_pdf(
    pdf_bytes: bytes,
    *,
    client: genai.Client | None = None,
    model: str | None = None,
) -> tuple[PatientChart, list[dict]]:
    """Send the PDF to Gemini and return (validated PatientChart, flagged fields).

    Individually-invalid values are quarantined into `flagged` rather than failing
    the whole chart. `client`/`model` are injectable for testing.
    """
    client = client or genai.Client(api_key=GEMINI_API_KEY)
    response = _generate_with_retry(
        client,
        model=model or GEMINI_MODEL,
        contents=[
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            EXTRACTION_PROMPT,
        ],
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )

    return validate_with_salvage(json.loads(response.text))
