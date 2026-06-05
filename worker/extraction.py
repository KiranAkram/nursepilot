"""Gemini-backed extraction: SNF referral PDF -> PatientChart."""

import json

from google import genai
from google.genai import types

from config import GEMINI_API_KEY, GEMINI_MODEL
from schemas import PatientChart

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


def extract_chart_from_pdf(
    pdf_bytes: bytes,
    *,
    client: genai.Client | None = None,
    model: str | None = None,
) -> PatientChart:
    """Send the PDF to Gemini and return a validated PatientChart.

    `client`/`model` are injectable for testing.
    """
    client = client or genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model=model or GEMINI_MODEL,
        contents=[
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            EXTRACTION_PROMPT,
        ],
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )

    return PatientChart.model_validate(json.loads(response.text))
