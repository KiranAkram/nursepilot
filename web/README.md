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

## Deploy

Deployed as a **Render static site** — no Docker image, no nginx. Settings:

| Field | Value |
|---|---|
| Root Directory | `web` |
| Build Command | `npm ci && npm run build` |
| Publish Directory | `dist` |
| `VITE_API_URL` | the API's URL, e.g. `https://nursepilot-api.onrender.com` |

`VITE_API_URL` is **baked in at build time** (`src/lib/api.ts` reads
`import.meta.env.VITE_API_URL`, falling back to `http://localhost:8000`).
Changing it needs *Manual Deploy → Clear build cache & deploy* — a restart
won't pick it up. Point it at the **api** URL: aimed at the web URL, the app
reads its own origin as the API and every response is `index.html`
(`<!doctype...is not valid JSON`).

Render auto-deploys on every push to `main`. CI typechecks (`tsc -b`) and
builds, but does not deploy.
