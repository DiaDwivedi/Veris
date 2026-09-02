# AI Finance Controller MVP

This project provides a robust, deterministic reconciliation engine for financial records. It is designed to match Merchant Records (e.g., Stripe, Square) against Bank Statement Records without moving money, mutating data, or silently discarding anything.

## Project Overview

The AI Finance Controller reconciles financial transactions against merchant/order records using a deterministic reconciliation engine. It classifies results into `AUTO`, `REVIEW`, and `UNMATCHED` categories. It provides a human review dashboard that supports persistent human overrides, preserving the deterministic results completely separately from human decisions.

## Architecture

The system is separated into a deterministic core, a stateful API wrapper, and a React frontend:

```text
       React Frontend
             |
             v
      FastAPI API Layer
             |
             +--------------------+
             |                    |
             v                    v
    Frozen Deterministic    SQLite Override
    Reconciliation Engine   State Layer
             |                    |
             +---------+----------+
                       |
                       v
               Wrapped v2 Response
                       |
                       v
              Financial Ledger UI
```

- **Deterministic API (v1)** remains stateless and deterministic.
- **Override-aware API (v2)** introduces state only as a wrapper.
- **SQLite Database** stores deterministic snapshots and human decisions.
- **React Frontend** never performs reconciliation logic.
- **Frozen Deterministic Boundary**: The deterministic engine is intentionally frozen and must not be modified. Matching logic is not modified by human overrides. The following files are frozen:
  - `app/pipeline/engine.py`
  - `app/pipeline/matcher.py`
  - `app/pipeline/scorer.py`
  - `app/pipeline/normalizer.py`
  - `app/models/domain.py`

*Note: Scoring weights, thresholds, safety gates, evaluation datasets, and evaluation scripts must not be modified without a deliberate engine-versioning decision.*

## Core Pipeline

1. **Merchant Upload**: Ingestion of CSV/API data.
2. **Data Normalizer**: Standardizes fields (currency, dates).
3. **Candidate Generator**: Creates possible matches based on heuristic blocking.
4. **Matching Engine**: Deterministic rules-based reconciliation.
5. **Confidence Scoring**: Non-probabilistic scoring indicating rule confidence.
6. **Decision Routing**: `AUTO`, `REVIEW`, `UNMATCHED`.
7. **Explanation**: Clear reasoning for every decision.
8. **Audit Trail**: Step-by-step trace of how a result was reached.

## Principles

- **No LLM Matching**: Matches are purely deterministic. LLMs may only be used for summarizing explanations later.
- **No Money Movement**: Read-only evaluation.
- **Strict Audibility**: Every decision must be explainable.
- **Safety First**: Low confidence pairs always go to REVIEW.

## API Documentation

### Deterministic API v1

- `POST /api/v1/reconcile/single`
- `POST /api/v1/reconcile/batch`

The v1 API directly exposes deterministic reconciliation results. It has no dependency on SQLite overrides and remains strictly backward compatible.

### Override-aware API v2

- `POST /api/v2/reconcile/batch`

The v2 API wraps the deterministic engine with state:
1. It runs the frozen deterministic reconciliation.
2. It persists the deterministic snapshot.
3. It retrieves any historical override.
4. It compares the override candidate ID with the current deterministic candidate.
5. It exposes the `manual_override` field only when the override still applies. If a candidate changes (due to external data updates or engine versioning), this results in `"manual_override": null` rather than incorrectly applying an old decision to a new candidate.

### Human Override API

- `POST /api/v1/overrides/approve`
- `POST /api/v1/overrides/reject`

These endpoints allow human reviewers to override deterministic output:
- Overrides require an existing deterministic snapshot.
- Candidate IDs are server-validated.
- Identical repeated actions are idempotent.
- Conflicting actions return a `409 Conflict`.
- Overrides do not modify the deterministic engine's output.

## Human Override Design

- **Deterministic truth**: The engine produces its result independently.
- **Human decision**: A human may approve or reject the deterministic candidate.
- **Historical preservation**: Human decisions remain stored historically.
- **Applicability**: A historical override is only shown when the current deterministic candidate exactly matches the candidate originally acted upon.

| Scenario | Override Returned |
| :--- | :--- |
| Candidate unchanged | Yes |
| Candidate changed | No (null) |
| Candidate disappears | No (null) |
| Same candidate after reprocessing | Yes |

## Frontend Documentation

The frontend uses React + Vite + TypeScript, styled with Vanilla CSS in a "financial-ledger" visual design. It provides:
- v2 reconciliation integration
- Expandable transaction rows
- Audit trail viewing
- Approve/Reject workflow
- Inline conflict error handling

**Important**: The frontend strictly does not perform matching, does not calculate alternative candidates, and does not bypass backend validation.

## Local Setup Instructions

### Backend

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   ```
2. Activate the virtual environment:
   ```bash
   .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the server:
   ```bash
   .venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

### Frontend

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```
   The local URL is typically `http://localhost:5173/`.

## Testing Instructions

### Backend
Run the backend test suite using `pytest`:
```bash
.venv\Scripts\pytest tests\
```

### Frontend
Run the frontend test suite using `vitest`:
```bash
cd frontend
npx vitest run
```

### Production Build
Test the production build process:
```bash
cd frontend
npm run build
```

## Known Limitations

- **Database**: SQLite is appropriate for the current local/small-scale application. A scaled multi-user deployment may eventually require a stronger database and concurrency strategy.
- **Stress Testing**: Explicit concurrent override stress testing is not yet implemented.
