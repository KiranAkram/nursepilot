"""Document screening: is this PDF an SNF referral packet at all?

First pipeline stage, before anything is sent to Gemini, so junk uploads never
reach the extractor. Uses TypeSafe's Jev decision model: text of the first pages
in, a calibrated yes/no probability out. Strict by design: if screening can't
run, the job fails rather than silently skipping the gate.
"""

import io
import os
import time
from datetime import UTC, datetime

import httpx
from pypdf import PdfReader

JEV_URL = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"
THRESHOLD = 0.5  # P(is SNF packet) below this is rejected; calibrate against real uploads
TIMEOUT_SECONDS = 10.0
QUESTION = (
    "This text is from a hospital discharge summary or a referral packet sent to a "
    "skilled nursing facility (SNF) for a single patient: it contains things like "
    "patient demographics, an admission/discharge, diagnoses, medications, or care "
    "instructions."
)

HEAD_PAGES = 2  # text from this many pages is plenty to classify
MAX_CHARS = 12_000  # well under Jev's 32k-token state limit
_MAX_ATTEMPTS = 3  # short: a down API should be reported fast, not after a minute
_RETRYABLE = {429, 500, 502, 503, 504}


class NotAnSnfPacketError(ValueError):
    """Screening ran and said no. Carries the verdict for the row."""

    def __init__(self, screening: dict):
        super().__init__("Not an SNF referral packet.")
        self.screening = screening


class ScreeningUnavailableError(RuntimeError):
    """Screening could not run (missing config, network, bad response)."""


def _api_key() -> str:
    key = os.environ.get("TYPESAFE_API_KEY", "")
    if not key:
        raise ScreeningUnavailableError("TYPESAFE_API_KEY is not set")
    return key


def head_text(pdf_bytes: bytes, pages: int = HEAD_PAGES) -> str:
    """Text of the first `pages` pages, capped at MAX_CHARS."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    parts = [page.extract_text() or "" for page in reader.pages[:pages]]
    return "\n".join(parts).strip()[:MAX_CHARS]


def _ask_jev(text: str, *, key: str, http: httpx.Client | None) -> tuple[float, str]:
    """POST one noul question; return (probability, answering model version)."""
    body = {
        "state": text,
        "model": MODEL,
        "questions": {"is_snf_packet": {"type": "noul", "instructions": QUESTION}},
    }
    headers = {"Authorization": f"Bearer {key}"}
    client = http or httpx.Client(timeout=TIMEOUT_SECONDS)
    try:
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                resp = client.post(JEV_URL, json=body, headers=headers)
            except httpx.HTTPError as exc:
                if attempt == _MAX_ATTEMPTS:
                    raise ScreeningUnavailableError(f"screening request failed: {exc}") from exc
                time.sleep(2 ** (attempt - 1))
                continue
            if resp.status_code in _RETRYABLE and attempt < _MAX_ATTEMPTS:
                time.sleep(2 ** (attempt - 1))
                continue
            if resp.status_code != 200:
                raise ScreeningUnavailableError(f"screening returned HTTP {resp.status_code}")
            try:
                data = resp.json()
                score = float(data["answers"]["is_snf_packet"]["noul"])
            except (ValueError, KeyError, TypeError) as exc:
                raise ScreeningUnavailableError(f"unexpected screening response: {exc}") from exc
            return score, str(data.get("model", MODEL))
        raise ScreeningUnavailableError("screening retries exhausted")
    finally:
        if http is None:
            client.close()


def screen_pdf(pdf_bytes: bytes, *, http: httpx.Client | None = None) -> dict:
    """Return the screening verdict for the row; raise if rejected or unavailable.

    Jev is text-only, so a PDF with no extractable text (a scan) can't be
    screened and is treated as unavailable rather than waved through.
    """
    key = _api_key()
    text = head_text(pdf_bytes)
    if not text:
        raise ScreeningUnavailableError("no extractable text to screen")

    score, model_version = _ask_jev(text, key=key, http=http)
    verdict = {
        "outcome": "accepted" if score >= THRESHOLD else "rejected",
        "score": round(score, 4),
        "threshold": THRESHOLD,
        "model": model_version,
        "at": datetime.now(UTC).isoformat(),
    }
    if verdict["outcome"] == "rejected":
        raise NotAnSnfPacketError(verdict)
    return verdict
