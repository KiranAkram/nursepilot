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

## Docker / deploy

Multi-stage `Dockerfile`: Node builds the static SPA, nginx serves it.

The API URL is **injected at container startup**, not baked at build time — so
one image is promoted unchanged through dev → staging → prod. At startup
`docker-entrypoint.sh` writes `/config.js` from the `API_URL` env var, and the
app reads `window.__APP_CONFIG__.apiUrl` (`src/lib/api.ts`). In local
`npm run dev` the `config.js` placeholder is ignored and the app falls back to
the build-time `VITE_API_URL`.

```bash
docker build -f Dockerfile -t nursepilot-web .
docker run -e API_URL=https://your-api... -p 8080:80 nursepilot-web
```

CI typechecks + builds + builds the image; the publish job pushes
`nursepilot-web` to GHCR; `cd.yml` deploys it to each environment's
`nursepilot-<env>-web` container app with that env's `API_URL`.
