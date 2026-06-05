"""Lite extraction eval. Run: GEMINI_API_KEY=... uv run python eval.py

Extracts every sample PDF, prints the grounding rate + ungrounded fields, and
dumps each chart to eval_out/<case>.json for manual review (hallucinations,
missing meds — the things the number won't show).
"""

import json
from pathlib import Path

from dotenv import load_dotenv

# Load repo-root .env before importing config (which reads GEMINI_API_KEY at import).
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from extraction import extract_chart_from_pdf  # noqa: E402
from verification import extract_page_texts, verify_chart  # noqa: E402

DATA_DIR = Path(__file__).resolve().parents[1] / "shared" / "data"
OUT_DIR = Path(__file__).resolve().parent / "eval_out"


def main() -> None:
    pdfs = sorted(DATA_DIR.glob("snf_packet_case*.pdf"))
    if not pdfs:
        raise SystemExit(f"No PDFs in {DATA_DIR}")
    OUT_DIR.mkdir(exist_ok=True)

    for pdf in pdfs:
        pdf_bytes = pdf.read_bytes()
        chart = extract_chart_from_pdf(pdf_bytes)
        grounding = verify_chart(chart, extract_page_texts(pdf_bytes))

        total = len(grounding)
        grounded = sum(g.grounded for g in grounding)
        pct = (grounded / total * 100) if total else 0
        ungrounded = [g.field for g in grounding if not g.grounded]

        print(f"\n{pdf.stem}: {grounded}/{total} grounded ({pct:.0f}%)")
        if ungrounded:
            print("  ungrounded: " + ", ".join(ungrounded))

        out = OUT_DIR / f"{pdf.stem}.json"
        out.write_text(json.dumps(chart.model_dump(mode="json"), indent=2))

    print(f"\nCharts written to {OUT_DIR} — skim for hallucinations / missing items.")


if __name__ == "__main__":
    main()
