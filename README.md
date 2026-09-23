# NursePilot

**SNF referral automation.** NursePilot ingests hospital discharge packets (PDFs), extracts structured patient data with an LLM, verifies every extracted fact against its source page, and presents the result in an EHR-style interface to assist skilled-nursing-facility handoff workflows.

Every extracted value carries a reference back to the exact page and quote it came from — clinical trust depends on traceability, not just extraction.

**▶ Try it: [nursepilot-web.onrender.com](https://nursepilot-web.onrender.com/)** — free-tier hosting, so the first request may take a minute to wake the API.

---

## Architecture

One backend process, one database, one static frontend. **Postgres is both the data store and the job queue** — there is no separate broker.

```
┌──────────────┐   upload PDF / poll / edit   ┌──────────────────────────────────┐
│   Web UI     │ ───────────────────────────▶ │  API process (FastAPI)           │
│ (React/Vite) │ ◀─────────────────────────── │                                  │
└──────────────┘                              │  HTTP routes ──┐                 │
                                              │                │ INSERT + NOTIFY │
                                              │                ▼                 │
                                              │         ┌────────────┐           │
                                              │         │  Postgres  │           │
                                              │         │ extractions│           │
                                              │         └─────┬──────┘           │
                                              │               │ LISTEN / claim   │
                                              │               ▼                  │
                                              │  Worker thread                   │
                                              │   screen (Jev) → extract (Gemini)│
                                              └──────────────────────────────────┘
```

| Component | Role |
|-----------|------|
| **`api/`** | FastAPI. Public HTTP surface (`/charts`, `/health`). On upload it stores the PDF bytes on a `pending` row and fires a Postgres `NOTIFY`. On startup it launches the extraction worker as an in-process daemon thread. |
| **`worker/`** | The extraction worker. `listener.py` blocks on `LISTEN` until a job arrives, `jobqueue.py` claims/retries/reclaims rows, `jobs.py` runs screening → extraction → grounding → persist; `screening.py` asks Jev whether the PDF is a discharge packet at all. Bundled into the API image; it has no container of its own. |
| **`shared/`** | Installable library: the clinical **schemas** and the **DB layer** (SQLModel models, session, `NOTIFY` helper). Used by both `api/` and `worker/`. |
| **`web/`** | Vite + React + TypeScript + Tailwind + shadcn/ui. History → upload → EHR-style chart view → edit → save. Deployed as a static site. |

**Why Postgres as the queue:** the job's state (`pending → screening → extracting → done`) already lived in the `extractions` table — a broker would only duplicate it. `NOTIFY` gives the worker an instant wake-up; `FOR UPDATE SKIP LOCKED` makes claiming a row atomic and safe even if several workers run.

---

## How a job flows

1. **`POST /charts`** — the API validates the upload (content type, `%PDF` magic bytes, 25 MB cap), inserts a `pending` row **with the PDF bytes on it**, and calls `pg_notify('extraction_jobs', job_id)` in the same transaction. Returns `202 { job_id }`.
2. The **worker thread** wakes from `LISTEN` and claims the oldest `pending` row (`status → screening`).
3. It **screens** the document first: the text of the first two pages goes to [Jev](https://typesafe.ai) (a yes/no decision model) with one question — *is this a hospital discharge / SNF referral packet?* Below the threshold the job ends as `rejected` and nothing is sent to Gemini. Otherwise `status → extracting`.
4. It sends the PDF to **Gemini** with the clinical schema in the prompt and validates the JSON against `PatientChart`. Individually invalid values are dropped and recorded in `flagged` so the rest of the chart still validates.
5. It **grounds** the result: for every `SourceRef`, the cited quote must appear on the cited page (per-page text via `pypdf`, segment-based fuzzy match).
6. It writes `status = done` with the immutable original chart, an editable working copy, the grounding report, and the flags — and **clears the PDF bytes**, which are only held while the job is in flight.
7. The **web UI** polls **`GET /charts/{job_id}`**, shows a retro splash as the gate decides (*packet get!* / *not an SNF packet* / *paused*), then renders the chart with per-fact source chips and saves edits via **`PUT /charts/{job_id}`**.

**Failure handling** (`worker/jobqueue.py`):

- A job that raises goes back to `pending` and is retried, up to **3 attempts**; after that it's marked `error` and its PDF is dropped.
- `NOTIFY` is only a wake-up hint. The worker also sweeps the table every **30 s**, so a notification missed during a restart costs at most 30 s of latency, never a lost job.
- A row stuck in `screening`/`extracting` for **20 min** (worker died mid-job) is requeued. That counts as a failed attempt, so a job that crashes the worker every time can't loop forever.
- Screening that can't run (Jev down, no extractable text) is a failure, not a pass: the job retries, then ends as `error` with `screening.outcome = unavailable`. Unscreened PDFs never reach Gemini.
- `rejected` rows are kept as the audit record of the gate but hidden from the history list.

---

## Repository layout

```
.
├── api/            # FastAPI service; hosts the worker thread; the only backend image
├── worker/         # Extraction worker: listener, job queue, screening, extraction + grounding
├── shared/         # Installable lib: clinical schemas + DB models/session/notify
├── web/            # Vite + React + TypeScript frontend (static site)
├── migrations/     # Alembic migrations (run from repo root)
├── docker-compose.yml   # local: api + postgres
└── .github/workflows/ci.yml
```

---

## Clinical data model

The top-level model is **`PatientChart`** (`shared/schemas/`), composed of sub-models such as `Demographics`, `Medication`, `LabReport`, and `VitalSigns`.

The load-bearing design choice: **every sub-model carries a `SourceRef`**:

```python
class SourceRef:
    page: int          # which PDF page the fact came from
    quote: str         # the supporting text on that page
    confidence: float  # the model's confidence
```

This makes every extracted fact traceable to its origin in the source document — the basis for the grounding step and for clinical trust.

The schema is derived from real SNF referral packets covering a range of clinical scenarios. Those source PDFs contain PHI and are **never committed** to the repository.

---

## API reference

| Method & path | Description |
|---------------|-------------|
| `POST /charts` | Upload a PDF (multipart). Stores it on a `pending` row and notifies the worker. Returns `202 { job_id }`. |
| `GET /charts` | History list, newest first. Rejected uploads are hidden unless `?include_rejected=true`. |
| `GET /charts/{job_id}` | Job status and, when done, the chart, grounding report, and flags. `404` if unknown. |
| `PUT /charts/{job_id}` | Overwrite the working chart with a full edited `PatientChart` (validated). `409` if the job isn't done, `422` if malformed. |
| `DELETE /charts/{job_id}` | Remove a finished job. `409` while in flight. The UI exposes this only with `?admin=1`. |
| `GET /health` | Liveness check → `{ "status": "ok" }`. |

The database is the source of truth: the row id *is* the job id. Statuses: `queued` → `screening` → `extracting` → `done` | `rejected` | `error`.

---

## Getting started (local)

Requires Docker, Node.js, and two API keys: Gemini (extraction) and TypeSafe/Jev (screening). Neither is needed for `/health` or unit tests.

```bash
cp .env.example .env          # dev defaults work; add GEMINI_API_KEY and TYPESAFE_API_KEY
docker compose up --build     # API → http://localhost:8000
uv run alembic upgrade head   # from the repo root
```

The `api` container runs both the HTTP server and the worker thread.

Frontend, in a separate shell:

```bash
cd web && npm install && npm run dev   # http://localhost:5173
```

The API's `CORS_ORIGINS` (default `http://localhost:5173`) must include the web origin.

---

## Running tests

Each service is tested independently. Worker unit tests mock Gemini and Jev and run fully offline.

```bash
cd api    && uv run pytest tests/
cd worker && uv run pytest tests/
```

Database-touching tests (upload lifecycle, job-queue claim/retry/reclaim semantics) skip unless `DATABASE_URL` points at a reachable Postgres. CI provides one and runs `alembic upgrade head` first.

The worker also has a gated evaluation against the real Gemini API, excluded by default:

```bash
cd worker && GEMINI_API_KEY=... uv run pytest -m eval tests/test_eval.py
```

---

## Deployment

Two services on Render, both free tier: the API as a **Docker web service** and the frontend as a **static site**. The API needs `DATABASE_URL`, `CORS_ORIGINS`, `GEMINI_API_KEY` and `TYPESAFE_API_KEY`. Render auto-deploys on every push to `main`; migrations are applied manually against Neon when a new one lands. Setup details are in `CLAUDE.md`.

**CI** (`.github/workflows/ci.yml`) runs on every push/PR: ruff lint, pytest for both services against an ephemeral Postgres, a `tsc` typecheck + Vite build for the frontend, and a Docker build of the API image. It does not deploy.

On the free tier the API spins down after 15 minutes without traffic and takes about a minute to wake. A job in flight keeps it awake, since the browser is polling; if it does stop mid-job, the stale-job sweep re-runs it on the next boot.

---

## Status & limitations

Early-stage. The local stack, CI, clinical data model, extraction pipeline, Postgres-backed job queue, upload/poll/edit API, and web frontend are in place. Extraction-quality work is deferred:

- Grounding can report false misses — a wrong cited page or a table mangled by PDF text extraction is not necessarily a hallucination.
- The "needs review" panel for flagged values is read-only; there's no accept/correct workflow yet.
- The chart editing UI covers Demographics and Vital Signs. The API accepts a full chart, so other sections can be wired in without API changes.
- The PDF is discarded after extraction; nurses verify against the quoted source text, not the original document.
- The screening threshold (`THRESHOLD = 0.5` in `worker/screening.py`) hasn't been calibrated against real uploads yet.
- Anyone with the link can upload. Delete is hidden behind `?admin=1`, not authenticated.
