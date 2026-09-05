# AI Finance Controller — Track 04

**Build spec · 3-day hackathon · deadline September 4, midnight**

> An AI Finance Controller that reconciles what it can prove, explains every decision, and knows when to ask a human.

This is the single source of truth: product plan, evaluation contract, repository
structure, module contracts, and frontend design. If something contradicts this
file, this file wins.

---

## 1. The core idea

Merchants have financial records scattered across payment gateways, orders,
invoices, bank settlements, and refunds. Matching these by hand is slow and
error-prone.

The system ingests financial records, normalizes inconsistent data, generates
candidate matches, scores match confidence, auto-reconciles high-confidence
matches, sends ambiguous cases to human review, honestly reports what it cannot
match, explains every decision, and logs a full audit trail.

> **The one sentence that matters**
> AI makes the recommendation. Rules constrain the decision. Humans handle uncertainty.

---

## 2. Non-negotiable safety principles

- The system never moves money or mutates financial records. It only proposes and
  reconciles relationships between existing records.
- Low-confidence matches are never auto-reconciled.
- Every decision is explainable, with underlying scores deterministic and auditable.
- Every human override is logged.
- LLM failure must never corrupt reconciliation — rule-based logic always has a
  fallback path.
- Unmatched records are never silently discarded.
- Scores are reported as "Match Confidence Score: X/100" — never framed as a
  statistical probability.

---

## 3. Architecture

```
Merchant upload
      ↓
Data normalizer
      ↓
Candidate generator
      ↓
Matching engine
      ↓
Confidence scoring
      ↓
┌─────────────┬─────────────┬─────────────┐
   AUTO MATCH      REVIEW       UNMATCHED
└─────────────┴─────────────┴─────────────┘
      ↓
AI explanation (template-first, LLM optional on top)
      ↓
Audit trail
```

Optional and gated: Isolation Forest as an anomaly/exception signal — never the
primary decision-maker.

**Tech stack.** Python, FastAPI, Pydantic, Pandas, SQLite, scikit-learn
(Isolation Forest, optional). LLM used only for explanation generation — never for
deciding matches. Frontend is plain HTML, CSS, and vanilla JS served as static
files by FastAPI: no npm, no bundler, no build step.

**Confidence thresholds** (configurable, validated against dev data, not universal
truths):

| Score | Decision |
| --- | --- |
| 90–100 | AUTO |
| 70–89 | REVIEW |
| below 70 | UNMATCHED |

---

## 4. Evaluation contract

*Written before any code touches the data. Committed before the dataset is opened.*

### Ground truth

A transaction is correctly reconciled when it maps to its known corresponding
order according to the dataset's ground-truth relationship. A transaction is
unmatched when no corresponding record exists. Ground truth is independent of the
model's confidence score and decision thresholds.

**Two distinct ground truths — do not conflate them:**

- **Pair ground truth** — `TXN_0002 → ORD_0002`, `TXN_0089 → NONE`. Defined
  independently, before any algorithm sees it.
- **Decision ground truth** — `TXN_0002 → AUTO`, `TXN_0078 → REVIEW`. What correct
  system behavior should be.

### Dataset

Generated independently, seeded and deterministic. Actual composition:

| Split | Records | AUTO | REVIEW | UNMATCHED |
| --- | --- | --- | --- | --- |
| Development | 68 | 37 | 24 | 7 |
| Held-out test | 32 | 18 | 11 | 3 |

Scenario coverage across both splits: exact match, date discrepancy, amount
discrepancy, missing reference, messy text, duplicate-looking, ambiguous
(multiple plausible candidates), genuinely unmatched.

Schema for both `transactions` and `orders`:
`id, amount, date, customer_id, reference, description`

Ground truth: `transaction_id, true_order_id, scenario, decision_ground_truth`

### Decision policy

- **AUTO** — high-confidence match supported by sufficient evidence.
- **REVIEW** — plausible candidate exists, evidence insufficient for automation.
- **UNMATCHED** — no sufficiently credible candidate exists.

### Metrics

Auto-match precision, auto-match recall, auto-match rate, review rate, unmatched
rate. Nothing else. No F1, no ROC, no confusion matrices.

### Split discipline

Thresholds and weights are tuned on the 68-record dev set only. The 32-record test
set is run **once**, near the end, with no further tuning afterward. This is what
lets you honestly say "evaluated against a held-out test set with known ground
truth" instead of "here are our results."

**Demo numbers are never hardcoded or curated.** Whatever the final held-out run
produces is what gets shown. 91% is more credible than a suspiciously perfect 97%.

---

## 5. Project structure

The organizing rule: **the engine must not import FastAPI, and the API must not
contain matching logic.** Everything else follows from that.

```
finance-controller/
├── EVALUATION_CONTRACT.md      written first, committed before data is touched
├── config.py                   thresholds + signal weights, single source
├── data/                       generated dataset, treated as read-only
│   ├── dev_transactions.csv
│   ├── dev_orders.csv
│   ├── dev_ground_truth.csv
│   ├── test_transactions.csv
│   ├── test_orders.csv
│   └── test_ground_truth.csv
├── engine/                     pure Python. no web, no LLM, no I/O
│   ├── schemas.py              Transaction, Order, Candidate, Decision, RunResult
│   ├── normalize.py            dates, amounts, casing, whitespace, references
│   ├── candidates.py           blocking / candidate generation
│   ├── scoring.py              per-signal scores → total out of 100
│   ├── decide.py               score + rules → AUTO / REVIEW / UNMATCHED
│   ├── explain.py              template explanations (the guaranteed path)
│   └── pipeline.py             reconcile(txns, orders, config) -> RunResult
├── llm/
│   └── phrase.py               optional rewrite of a template explanation
├── api/
│   ├── main.py                 app, static mount, startup
│   ├── routes.py               upload, run, results, detail, review
│   ├── models.py               Pydantic request/response models
│   └── store.py                SQLite: runs, decisions, overrides
├── evaluation/
│   ├── run_eval.py             engine vs ground truth, no server needed
│   └── results/                dated JSON output, never edited by hand
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── style.css
├── generator/                  dataset model's territory, nothing else writes here
│   └── dataset_generator.py
└── tests/
    └── test_scoring.py         boundary cases only
```

### Why it is shaped this way

**The engine is isolated** because the Day 1 checkpoint is at 3 PM and the API
doesn't exist until Day 2. If matching logic lives inside route handlers, the
evaluation script can't run without booting a server, and the hostile QA model has
to reason about HTTP to attack a scoring function.

**`config.py` sits at the root**, not inside `engine/`. Thresholds are tuned on dev
and frozen before the test run. One file at the top level makes "we tuned only on
dev" a thing you can point at, and makes the freeze a single visible commit.

**`explain.py` is in the engine but `llm/` is outside it.** Templates are part of
the deterministic path and must work when the network doesn't. The LLM layer takes
a finished explanation and rephrases it. If it throws, times out, or returns
garbage, `phrase.py` catches and returns the input unchanged. One try/except, one
fallback, no branching in the pipeline.

**The frontend is static files served by FastAPI.** One process, no CORS, no build
step that can break at 11 PM on Day 2. Three screens rendering fewer than 40 rows
of data — a framework earns nothing here and costs a toolchain.

### Deliberately not created

- A `services/` or `repositories/` layer. One data source, one workflow —
  indirection with nothing to abstract.
- Docker. Nothing about a laptop demo needs it, and a broken image at midnight is a
  self-inflicted outage.
- Git branching. A single shared file for parallel output is simpler and safer
  under time pressure.

---

## 6. Core contracts

Fix these early — everything else plugs into them.

### The one signature that matters

```python
reconcile(transactions, orders, config) -> RunResult
```

Pure function. No database, no network, no timestamps generated inside it. The API
calls it and writes the result to `store.py`. `run_eval.py` calls it and compares
against ground truth. Same code path in both, which is what lets you say the demo
runs the same engine the evaluation measured.

### Decision record

Every transaction produces one of these, including unmatched ones:

```
transaction_id
proposed_order_id        null when unmatched
confidence_score         integer, 0-100
decision                 AUTO | REVIEW | UNMATCHED
signal_scores            per-signal earned/max breakdown
competing_candidates     ranked list with scores
explanation              string, template-generated minimum
explanation_source       template | llm
```

### Signal weights

Live in `config.py`, sum to 100. Starting point, tuned on dev only:

| Signal | Max | Rationale |
| --- | --- | --- |
| Reference | 25 | Strongest identifier when present |
| Amount | 35 | Strongest signal overall, exact or within tolerance |
| Date | 20 | Graduated by days apart |
| Customer ID | 12 | Strong corroborator |
| Description | 8 | Weakest — cut this first if scope is cut |

**Never reduce to amount + date alone.** Two unrelated ₹5,000 same-day
transactions is a realistic collision and a real false positive. If the fallback is
needed, cut the weakest signal (description), not the strong ones.

### API surface

```
POST  /api/runs              upload CSVs, run reconciliation, return run_id
GET   /api/runs/{id}         summary counts + all decision rows
GET   /api/runs/{id}/records/{txn_id}   full detail incl. signals + candidates
POST  /api/records/{txn_id}/review      confirm | reassign | mark unmatched
GET   /api/records/{txn_id}/audit       full audit trail
GET   /api/evaluation        latest held-out metrics
```

Every review action writes an override row with timestamp, prior decision, new
decision, and reviewer note. Overrides never mutate the original decision row.

---

## 7. Frontend design

Three screens. The frontend's job is not to look impressive — it is to make the
trust story visible. Three claims must be provable on screen in 90 seconds: the
system explains itself, it routes uncertainty to humans instead of guessing, and it
admits what it cannot match.

The test set is 32 records. The entire run fits on one screen. Do not build
pagination for 32 rows.

### Screen 1 — Run summary

Loads immediately after upload.

**Header.** Run label, source filename, record counts, timestamp.

**Four metric cards.** Auto-matched (count, percentage, threshold), needs review,
unmatched, auto-match precision (as `17 of 18 correct`, not a bare percentage).
Green tint for auto, amber for review, neutral for unmatched.

**Safety line, directly under the cards.** *"Proposals only. No records were
modified and no money moved."* Small, muted, always visible. It answers the
question a finance judge asks first.

**Filter chips.** All / Auto / Review / Unmatched, with counts baked into the label.

**Results table.** Five columns: Transaction (id, amount, date), Proposed match,
**Why**, Score (`74/100`), Decision badge.

The **Why** column is the most important design decision on the screen. Most
reconciliation tools show a score and nothing else, and the judge immediately asks
"why 78?" — which you then have to answer verbally. A one-line reason in the table
means the question never gets asked. Examples: "Reference + amount + customer all
agree", "Amount off by ₹50 — outside tolerance", "Three orders fit equally — no
tiebreaker", "No candidate cleared the floor".

### Screen 2 — Record detail

This is where the pitch lives. Opens on clicking any row.

**Header.** Transaction id, full field values including which fields are absent,
and the confidence score with its decision badge, right-aligned and large.

**Signal breakdown.** One row per signal: label, a horizontal bar showing
earned/max, and the outcome in words (`exact 35/35`, `1 day apart 16/20`,
`absent 0/25`, `differs 0/12`). Footer line: *"Deterministic weights. Same input,
same score, every run."*

Bars, not a single progress ring. A ring says "the model is 74% sure of something."
Bars say "here is exactly which evidence was present and which was missing." That
is the difference between a probability claim you cannot defend and an audit
artifact you can — and it encodes the "never a statistical probability" rule
directly into the UI.

**Competing candidates.** Ranked list of every candidate that cleared the floor,
with amount, date, customer, and score. Top candidate outlined, rest plain.

This block is the strongest asset in the whole build. Anyone can render
"confidence: 74". Showing three orders scoring 74, 72, and 71 is visual proof that
REVIEW is a reasoned decision and not a dumping ground for whatever the engine
found hard. It also makes the AMBIGUOUS scenario self-explanatory.

**Explanation.** Two or three plain sentences. Below it, a small provenance badge:
`Template-generated` or `LLM phrasing`. Show the fallback badge, do not hide it — it
looks like an admission of failure and is the opposite. It proves the explanation
layer degrades gracefully instead of breaking the demo.

**Reviewer decision.** Three buttons: Confirm proposed match, Pick another
candidate, Mark unmatched.

**Audit trail.** Timestamped lines: ingested, candidates generated with top score,
routing decision with the threshold that triggered it, then any override history.

### Screen 3 — Evaluation

Thin and static. Dev/test split sizes, the frozen thresholds, the signal weight
table, and the held-out metrics from the actual final run with its timestamp. This
is the page you open when a judge asks how you know it works.

### Design rules

- **Do not make UNMATCHED look like an error state.** No red badges, no warning
  icons, no "issues" tab. Unmatched rows stay visually neutral, same weight as
  every other row, with "None" where the match would be. The entire positioning is
  that honest non-answers are a feature — if it looks like failure on screen, the
  UI is arguing against the closing line.
- No pie chart of the three buckets. The metric cards already carry those numbers;
  a pie chart of 18/11/3 is decoration.
- No settings page, no user management, no login.
- Amber for review, green for auto, neutral gray for unmatched. Red is unused.

---

## 8. The 3-day schedule

### Day 1 — engine, dataset, reality check (hard stop 11 PM)

| Time | Task |
| --- | --- |
| 9:00–9:30 | Schemas + write the evaluation contract before any code touches data |
| 9:30 | Fire off dataset generator in parallel |
| 9:30–1:00 | Core engine: normalization → candidates → weighted-signal matching → scoring → buckets |
| 1:00–1:30 | Integrate dataset; one review pass, fix obvious issues, move on |
| 1:30–3:00 | Run against dev set, build evaluation metrics (precision, recall, rates only) |
| **3:00 PM** | **HARD CHECKPOINT — GO / NO-GO. No negotiating.** |
| 3:00–5:00 | If ahead: conditional embeddings for description similarity — keep only if it measurably beats string similarity on dev, delete otherwise |
| 5:00–6:00 | Hostile QA pass — triage for false-positive risks only, ignore style nitpicks |
| 6:00–7:00 | Fix only the 2–3 real bugs found. Stop. |

> **The 3 PM rule, verbatim**
> If engine + dataset + evaluation aren't functioning by 3 PM, you do not add
> features — no embeddings, no LLM, no anomaly layer, no fancy matching. You finish
> the core product. If the fallback is needed, freeze the simplest version that
> already works correctly — do not gut down to amount + date only.

By 11 PM: working engine, real labeled dataset, real evaluation numbers, known
false-positive risk. No UI, no API yet — correct for Day 1.

### Day 2 — API, workflow, audit (hard stop: evening)

| Block | Task |
| --- | --- |
| Morning | API layer: upload, run, results, detail — wiring around an engine that already works |
| Midday | Review endpoints (confirm/reassign/unmatch) + audit logging on every decision and override |
| Afternoon | Explanation layer — templates first (guaranteed fallback), LLM layered on top only if time allows, never a live-demo dependency |
| Evening | Judge-model pass — fix only what threatens the pitch, ignore cosmetic feedback |

### Day 3 — UI, demo, stop building

| Block | Task |
| --- | --- |
| Morning | Three screens: run summary, record detail, evaluation |
| Midday | Full end-to-end run with real data; fix only bugs actually hit |
| Afternoon | Feature freeze. Crashes, confusing UI, broken demo paths only. No new functionality. |
| Evening | Rehearse the demo narrative out loud |

---

## 9. Parallel model workflow

> **Golden rule**
> Parallelize independent deliverables, not the whole project. You remain the sole
> integrator — no two models modify the same codebase simultaneously.

| Job | Tool | Why |
| --- | --- | --- |
| Core reconciliation engine | Claude Code | Critical path — keep it on the strongest coding agent |
| Dataset + ground truth generator | Gemini Pro | Independent reasoning; keeps ground truth from being shaped by the implementation |
| Hostile QA / break the system | GPT | A fresh model attacking the engine catches different blind spots than the one that built it |
| API / security review | GPT | Fresh perspective on validation, unsafe states, edge cases |
| Judge-model review | Gemini Pro or GPT | Attacks the positioning, not the code |
| UI implementation | Claude Code | Keep codebase implementation with the primary agent |
| Cheap repetitive tasks | OpenRouter free model | Utility only — test cases, CSV conversion, boilerplate. Never the matching algorithm, evaluation methodology, or final security review. |

**Integration discipline.** The dataset model writes only to `generator/` and
`data/`. One source of truth, one person merging. A messy merge at 11 PM is worse
than skipping the parallel workflow entirely.

**On the QA bug report.** Triage immediately for false-positive risks only. A report
with 15 findings is not a to-do list — fix the 2–3 that matter, ignore the rest.
Treating it as a checklist is how Day 1 evening disappears.

---

## 10. Demo narrative

Rehearsed out loud, Day 3 evening.

1. **Problem.** Merchants have financial records spread across multiple systems;
   reconciliation is still heavily manual.
2. **Solution.** Our AI Finance Controller automatically reconciles what it can
   prove — and knows when to stop and ask a human.
3. **Demo.** Upload the held-out test batch → show the real, uncurated summary.
4. Open the three-way ambiguous case → show competing candidates scoring within two
   points, correctly routed to REVIEW.
5. Open a genuinely unmatched record → show it honestly reported, not forced.
6. Open the audit trail → timestamp, evidence, confidence, decision, override
   history.
7. Open the evaluation screen → dev/test split, frozen thresholds, held-out metrics.

**Do not open on an exact match.** Everyone believes those work. Lead with the
ambiguous case.

> **Closing line**
> "The goal isn't to automate every decision. It's to automate the decisions we can
> trust — and surface the ones we can't."

---

## 11. What was deliberately cut

| Cut | Reason |
| --- | --- |
| Git branching workflow | Adds risk under time pressure unless already fluent |
| Embeddings by default | Conditional, Day-1-afternoon only, kept only if it beats string similarity on dev |
| LLM as decision-maker | Explanation layer only; matching stays rule-based and auditable |
| F1, ROC, confusion matrices | Precision/recall/rates is sufficient; more looks like padding, not rigor |
| Full QA bug list as a checklist | Only false-positive-risk items get fixed |
| "97% probability" framing | Replaced with "Match Confidence Score: X/100" |
| React, npm, bundler | Three screens, 40 rows — a toolchain that can only break |
| Docker | A broken image at midnight is a self-inflicted outage |
| Multi-agent architecture, real payments, mobile app, microservices | Out of scope entirely |

---

## 12. Definition of done

- [ ] 32 records processed from the held-out test set
- [ ] Evaluation contract written before the dataset was seen by the algorithm
- [ ] Pair ground truth and decision ground truth defined independently
- [ ] Dev/test split respected — thresholds tuned only on dev, frozen before test run
- [ ] Engine produces AUTO / REVIEW / UNMATCHED correctly
- [ ] Every decision has an explanation (template minimum, LLM optional)
- [ ] Signal breakdown visible per record
- [ ] Competing candidates visible for ambiguous cases
- [ ] Human review + override logging works
- [ ] Full audit trail exists per record
- [ ] At least one failure case demonstrated live (missing reference, low confidence)
- [ ] Metrics reported honestly and uncurated from the actual final run
- [ ] Frontend works end-to-end without manual intervention
- [ ] System never moves money or mutates records — proposal only

> **Primary objective**
> Ship a trustworthy MVP first. Everything else is secondary.

---

## The one rule for the next 3 days

**A working boring feature beats an impressive unfinished feature.**

If embeddings are amazing, keep them. If mediocre, kill them. If the LLM is flaky,
template it. If the UI isn't fancy, it doesn't matter. If the matching engine works
reliably, you have a project.

At 3 PM Day 1: GO → continue. NO-GO → cut scope. No negotiating with yourself.
