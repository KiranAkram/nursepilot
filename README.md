# NursePilot

**SNF referral automation.** NursePilot ingests hospital discharge packets (PDFs), extracts structured patient data using an LLM, verifies every extracted fact against its source page, and presents the result in an EHR-style interface to assist skilled-nursing-facility (SNF) handoff workflows.

Every extracted value carries a reference back to the exact page and quote it came from — clinical trust depends on traceability, not just extraction.

---

## Table of contents

- [What it does](#what-it-does)
- [End-to-end flow](#end-to-end-flow)
- [Architecture](#architecture)
- [Repository layout](#repository-layout)
- [Tech stack](#tech-stack)
- [Clinical data model](#clinical-data-model)
- [API reference](#api-reference)
- [Getting started (local)](#getting-started-local)
- [Running tests](#running-tests)
- [Deployment](#deployment)
- [Project status & limitations](#project-status--limitations)

---

## What it does

1. **Ingest** — a hospital discharge packet (PDF) is uploaded through the web UI or API.
2. **Extract** — a background worker sends the PDF to an LLM (Google Gemini) and gets back a structured patient chart.
3. **Validate** — the LLM output is validated against a strict clinical schema. Individually invalid values are dropped and flagged rather than failing the whole document.
4. **Ground** — every fact's cited quote is checked against the text of the page it claims to come from, so hallucinated or mis-cited data is surfaced.
5. **Persist** — the original (immutable) and working (editable) charts, plus grounding and flag results, are stored in Postgres.
6. **Review & edit** — the web UI renders the chart EHR-style with per-fact source chips, lets a nurse correct fields, and saves the edited version.

---

## End-to-end flow

```
                         ┌──────────────┐
        upload PDF        │              │   enqueue job (task name)
   ┌────────────────────▶ │   API        │ ─────────────────────────┐
   │                      │  (FastAPI)   │                          │
   │   poll status /      │              │                          ▼
   │   fetch chart        └──────┬───────┘                   ┌────────────┐
   │                             │                           │   Redis    │
┌──┴───────────┐                 │ read/write                │  (broker)  │
│   Web UI     │                 ▼                           └─────┬──────┘
│ (React/Vite) │          ┌────────────┐                          │ consume
└──────────────┘          │  Postgres  │ ◀──────────────┐         ▼
                          │ extractions│   persist       │  ┌────────────┐
                          └────────────┘   chart +       └──│   Worker   │
                                           grounding +      │  (Celery)  │
                                           flags            └─────┬──────┘
                                                                  │
                                                  ┌───────────────┴───────────────┐
                                                  │  Extraction pipeline           │
                                                  │  1. PDF → Gemini → JSON        │
                                                  │  2. validate (drop+flag bad)   │
                                                  │  3. ground quotes vs PDF pages │
                                                  └────────────────────────────────┘
```

**Step by step:**

1. **`POST /charts`** — the API validates the upload (content type, `%PDF` magic bytes, size cap), inserts a `pending` row in Postgres, then enqueues an extraction job to the worker over Redis. Returns a `job_id`.
2. The **worker** picks up the job, base64-decodes the PDF, and calls Gemini with the clinical schema embedded in the prompt.
3. Gemini returns JSON, which is validated against the `PatientChart` model. Invalid individual values are **dropped and recorded** in a `flagged` list so the rest of the chart still validates.
4. The worker **grounds** the result: for every fact's `SourceRef`, it checks that the cited quote actually appears on the cited PDF page (per-page text via `pypdf`, segment-based fuzzy matching).
5. The worker **upserts** the row: status → `done`, storing the immutable original chart, an editable working copy, the grounding report, and the flags.
6. The **web UI** polls **`GET /charts/{job_id}`** until the job is `done`, then renders the chart with source chips. Edits are saved via **`PUT /charts/{job_id}`**.

---

## Architecture

Two runnable services, one shared library, and a frontend — all in a single repository:

| Component | Role |
|-----------|------|
| **`api/`** | FastAPI. The public HTTP surface (`/charts`, `/health`), Postgres-backed. Enqueues work to the worker by task *name* over Redis — it never imports worker code, so LLM dependencies don't leak into the API image. |
| **`worker/`** | Celery. Background extraction pipeline (PDF → chart → grounding → flags). Owns all Gemini/PDF dependencies and persists each job to the database. |
| **`shared/`** | Installable library holding the clinical **schemas** and the **database layer** (SQLModel models + session). Consumed by both services as an editable path dependency. |
| **`web/`** | Vite + React + TypeScript frontend. History list → upload → EHR-style chart view with source chips → edit → save. Served by nginx; the API URL is injected at container startup (one image, per-environment configuration). |

**Shared infrastructure:**

- **Postgres** — primary data store. A single `extractions` table; schema managed by Alembic.
- **Redis** — Celery broker, result backend, and cache.

Each service has its own dependencies, Dockerfile, and test suite. The `shared` library is bundled into each service image at build time.

---

## Repository layout

```
.
├── api/            # FastAPI service — HTTP surface, Postgres-backed
├── worker/         # Celery worker — Gemini extraction + grounding pipeline
├── shared/         # Installable lib: clinical schemas + DB models/session
├── web/            # Vite + React + TypeScript frontend
├── migrations/     # Alembic migrations (run from repo root)
├── docker-compose.yml
└── .github/workflows/   # CI/CD
```

---

## Tech stack

**Backend**
- Python 3.12, [`uv`](https://github.com/astral-sh/uv) for dependency management
- FastAPI, Pydantic v2
- Celery (Redis broker)
- Google Gemini via `google-genai` (extraction); `pypdf` (per-page text for grounding)
- Postgres via SQLModel + psycopg 3; Alembic migrations

**Frontend**
- Vite + React + TypeScript
- Tailwind CSS + shadcn/ui

**Infrastructure**
- Docker + docker-compose (local)
- Azure Container Apps (deployed)
- GitHub Actions (CI/CD)
- Managed Postgres (Neon) and Redis (Upstash) in the cloud

---

## Clinical data model

The top-level model is **`PatientChart`** (`shared/schemas/`), composed of sub-models such as `Demographics`, `Medication`, `LabReport`, `VitalSigns`, and more.

The load-bearing design choice: **every sub-model carries a `SourceRef`**:

```python
class SourceRef:
    page: int          # which PDF page the fact came from
    quote: str         # the supporting text on that page
    confidence: float  # the model's confidence
```

This makes every extracted fact traceable to its origin in the source document — the basis for the grounding step and for clinical trust.

The schema is derived directly from real SNF referral packets covering a range of clinical scenarios. Those source PDFs contain PHI and are **never committed** to the repository.

---

## API reference

| Method & path | Description |
|---------------|-------------|
| `POST /charts` | Upload a PDF (multipart). Validates type, magic bytes, and size; inserts a `pending` row and enqueues extraction. Returns `202 { job_id }`. |
| `GET /charts/{job_id}` | Fetch job status and, when done, the chart, grounding report, and flags. `404` if unknown. |
| `PUT /charts/{job_id}` | Overwrite the working chart with a full edited `PatientChart` (validated). `409` if the job isn't done, `422` if malformed. |
| `GET /charts` | History list, newest first. |
| `GET /health` | Liveness check → `{ "status": "ok" }`. |

The database is the source of truth: the row id equals the job id equals the extraction task id, so status and results are always consistent across services.

---

## Getting started (local)

### Prerequisites

- Docker + Docker Compose
- Node.js (for the frontend)
- A Google Gemini API key (only needed for the extraction worker — not for `/health` or unit tests)

### 1. Configure environment

```bash
cp .env.example .env
# The dev defaults work as-is. Add GEMINI_API_KEY to enable extraction.
```

### 2. Start the backend stack

```bash
docker compose up --build
# API → http://localhost:8000   (GET /health → {"status": "ok"})
```

### 3. Apply database migrations

```bash
uv run alembic upgrade head   # from the repo root
```

### 4. Run the frontend

```bash
cd web
npm install
npm run dev   # http://localhost:5173
```

The API's allowed origins (`CORS_ORIGINS`, default `http://localhost:5173`) must include the web origin.

---

## Running tests

Each service is tested independently. Worker unit tests mock Gemini and run fully offline.

```bash
cd api    && uv run pytest tests/
cd worker && uv run pytest tests/
```

The worker also has a **gated evaluation** that calls the real Gemini API against sample PDFs. It's excluded by default; run it explicitly:

```bash
cd worker && GEMINI_API_KEY=... uv run pytest -m eval tests/test_eval.py
```

Database-touching tests skip automatically unless a reachable `DATABASE_URL` is configured.

---

## Deployment

All services are containerized and deployed to **Azure Container Apps**, with images published to a container registry by CI.

- **CI** (`ci.yml`) — on every push/PR: lint, test (against ephemeral Postgres + Redis), and build the images. On push to `main`, it also builds and publishes the API, worker, and web images.
- **CD** (`cd.yml`) — on a successful CI run on `main`, deploys the new images to the live environment.

Container Apps pull images using a managed identity (no registry passwords stored on the apps). Per-environment configuration (database URL, Redis URL, API key, frontend API URL) is supplied through GitHub Environment secrets and variables, never baked into images — the same image is promotable across environments.

---

## Project status & limitations

NursePilot is an early-stage project. The local dev stack, CI/CD, clinical data model, extraction pipeline, upload/poll/edit API, Postgres store, and web frontend are all in place.

Known limitations (extraction-quality work is deferred):

- Grounding can occasionally report false misses (a wrong cited page or a PDF table mangled during text extraction is not necessarily a hallucination).
- The "needs review" panel for flagged values is currently read-only — there is no accept/correct-flagged workflow yet.
- The chart editing UI covers Demographics and Vital Signs; the API accepts a full chart, so other sections can be wired in without API changes.
