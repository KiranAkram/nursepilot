"""Real Gemini extraction against the sample PDFs. Gated: `pytest -m eval`.

Requires GEMINI_API_KEY and the (gitignored) PDFs in shared/data/.
"""

from pathlib import Path

import pytest

from config import GEMINI_API_KEY
from extraction import extract_chart_from_pdf
from schemas import PatientChart
from verification import extract_page_texts, verify_chart

DATA_DIR = Path(__file__).resolve().parents[2] / "shared" / "data"
PDFS = sorted(DATA_DIR.glob("snf_packet_case*.pdf"))

pytestmark = [
    pytest.mark.eval,
    pytest.mark.skipif(not GEMINI_API_KEY, reason="GEMINI_API_KEY not set"),
    pytest.mark.skipif(not PDFS, reason="sample PDFs not present"),
]


@pytest.mark.parametrize("pdf_path", PDFS, ids=lambda p: p.stem)
def test_extracts_valid_grounded_chart(pdf_path):
    pdf_bytes = pdf_path.read_bytes()

    chart = extract_chart_from_pdf(pdf_bytes)
    assert isinstance(chart, PatientChart)
    assert chart.demographics.mrn

    grounding = verify_chart(chart, extract_page_texts(pdf_bytes))
    grounded = sum(g.grounded for g in grounding)
    assert grounded / len(grounding) >= 0.6, (
        f"{pdf_path.stem}: only {grounded}/{len(grounding)} facts grounded"
    )
