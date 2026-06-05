# NursePilot Web

EHR-style frontend: upload a discharge-packet PDF, view the extracted
`PatientChart`, and trace every fact back to its source page/quote.

Vite + React + TypeScript + Tailwind + shadcn/ui.

## Dev

```bash
cd web
npm install
cp .env.example .env   # point VITE_API_URL at the API (default http://localhost:8000)
npm run dev            # http://localhost:5173
```

The API must be running (and its `CORS_ORIGINS` must include the web origin —
defaults to `http://localhost:5173`). Upload flow: `POST /charts` → poll
`GET /charts/{job_id}` until the chart + grounding come back.

## How traceability is shown

Each extracted fact carries a **source chip** (`p<page> · <confidence>%`). Hover
to see the verbatim quote. The chip is colored by the grounding check:

- 🟢 grounded — the quote was found on the cited PDF page
- 🟡 ungrounded — the quote was not found there (paraphrase, wrong page, or
  table mangled by the PDF text extractor)

Types in `src/types/chart.ts` mirror `shared/schemas/patient_chart.py` — keep
them in sync when the schema changes.
