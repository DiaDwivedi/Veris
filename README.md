# VERIS

**Built to decide. Designed to prove..**

Deterministic transaction-to-order reconciliation with a full audit trail, a
held-out evaluation, and a measured LLM baseline.

**Live:** https://veris-4d52.onrender.com — free tier, so the first load can take
~50 seconds while the instance wakes.

**Demo:** [5-minute walkthrough](https://drive.google.com/file/d/1Frr4sWzPhrVrBuqZnSHVXPfPs9YfZSMz/view?usp=sharing)
---

## The Finding

The obvious way to build this in 2026 is to hand each transaction and its
candidate orders to a language model and ask which one matches. So that was the
first thing built here — as a baseline, not as the product.

Same 68 transactions, same ground truth, same metric functions, temperature 0,
uncached, run twice.

**The baseline beat the deterministic engine on recall — 83.6% against 63.9% —
and matched it on precision at 100%.** It was also perfectly reproducible: zero
of 68 decisions differed across two identical runs.

That result is on the evaluation screen in the app, marked as a loss, because it
is one.

Reconciliation has an asymmetry that makes this matter: a wrong auto-match marks the record resolved and removes it from the queue, so nobody goes looking for it again. A missed match stays in the queue where someone eventually finds it. One failure is silent, the other is self-correcting — which is why the system is tuned to decline rather than to maximise matches, and why being able to show why a record was closed is worth trading recall for.

So the argument for the deterministic engine is not accuracy. It is that a
reconciliation decision needs properties accuracy doesn't cover: which signal
carried the decision, what threshold it crossed, a config you can freeze and
point at in a commit, and an override that is recorded as an override. The
baseline gave a better number and none of that.


The obvious objection: if the baseline is more accurate and needs far less review, why not let it decide and have the engine produce the audit trail afterwards?

The engine's answer and this is an argued position, not a demonstrated one , is that an explanation generated after a decision is a rationalisation, not a record. If the model picks the match and the engine explains it, the engine is reverse-engineering a justification for a choice it didn't make — and when they disagree, it would be describing evidence that doesn't support the outcome. A reason code from the model has the same problem: it's text produced in the same forward pass as the answer, with nothing tying it to what actually drove the output.

The engine's explanation isn't a description of the computation. It is the computation. That's the property that doesn't survive the swap.

A stronger version of the objection is to run both — let the model decide and generate the scorecard alongside as instrumentation. That has a different problem: it needs an answer to which decision governs when they disagree. Whichever you pick, one system is deciding and the other is producing an artifact about a choice it didn't make.

---

## Results

### Held-out test split — run once, config frozen

| Metric | Value |
| --- | --- |
| AUTO precision | **20 of 20 correct (100%)** |
| Candidate recall | 100% |
| AUTO-match recall | 69.0% |
| AUTO rate | 62.5% |
| REVIEW rate | 28.1% |
| UNMATCHED rate | 9.4% |

32 transactions the frozen config had never seen. Recall on test came out slightly higher than on dev (69.0% vs 63.9%). That's consistent with not overfitting, though 32 records is too few to conclude much from a five-point difference.

Artifact: `evaluation/results/evaluation_run_20260905_143611.json`

### Dev split — deterministic engine vs LLM baseline

Both on dev. Model `models/gemini-3.5-flash-lite`, temperature 0, prompt v1,
uncached.

| Metric | Engine | LLM baseline | Winner |
| --- | --- | --- | --- |
| AUTO precision | 100% | 100% | tie |
| AUTO-match recall | 63.9% | **83.6%** | baseline |
| AUTO rate | 57.4% | **75.0%** | baseline |
| REVIEW rate | 32.4% | **1.5%** | baseline |
| UNMATCHED rate | 10.3% | 23.5% | engine |
| Candidate recall | 100% | 85.2% | not comparable* |

\* The baseline only sees the top 10 candidates above the score floor, so its
lower candidate recall is an artifact of the harness, not a result.

### Reproducibility

```
0 of 68 decisions differed across identical uncached runs
Order ID differences   0
Decision differences   0
Parse failures         Run A 0 · Run B 0
Provider errors        Run A 0 · Run B 0
```

The original hypothesis was that the baseline would vary across identical runs. It didn't. Reported anyway.
The deterministic engine was run twice over the same dev split: **0 of 68
decisions differed**, comparing every field of every record, not just the
aggregate metrics.

Same number as the baseline — different kind of claim. The baseline was
reproducible on one model version, on one day, with a provider that can change
it without anything appearing in this repository. The engine is reproducible by
construction: `reconcile()` is pure, the config is a committed file, and there is
no source of variation that isn't visible in the call.

---

## How it decides

```
CSV upload
    │
    ▼
normalize ──► blocking ──► signal scoring ──► routing ──► explanation
                                                  │
                              ┌───────────────────┼───────────────────┐
                              ▼                   ▼                   ▼
                            AUTO                REVIEW            UNMATCHED
                          score ≥ 90         70 ≤ score < 90    no candidate
                                                  │              above floor
                                                  ▼
                                          human reviewer
                                                  │
                                                  ▼
                                        override, appended
```
The LLM appears nowhere in this path. It exists only in evaluation/llm_baseline.py, as a benchmark scored against the same ground truth — see the finding above.
Five signals, each returning earned/max plus a plain-language outcome:

| Signal | Weight |
| --- | --- |
| Reference ID | 50 |
| Amount — exact, *or* within tolerance | 35 / 10 |
| Date — exact, *or* proximity | 15 / 5 |
| Customer ID | 10 |
| Description match | 10 |

Amount and date weights are alternates, not additive, so the maximum achievable
score is 120.

**Known issue:** the reported score caps at 100 while the maximum achievable is
120. This compresses the top of the scale — a record earning 120 and one earning
100 both display as 100. It does not change routing, because the AUTO threshold
of 90 sits below the cap. Found during final verification and left in place
rather than re-tuning and invalidating the held-out run. It's disclosed on the
evaluation screen in the app too.

`reconcile(transactions, orders, config) -> RunResult` is a pure function — no
database, no network, no timestamps generated inside it. The API layer contains zero matching logic: app/api/endpoints.py imports only engine, calls engine.reconcile(), and persists the result. No scoring or matching function is called there.

Decision rows are immutable — there is no UPDATE path for them anywhere in app/api/. Reviewer overrides are inserts into a separate table (app/api/overrides.py) with timestamp, prior decision, new decision, and the selected candidate, and tests/test_overrides.py::test_v2_override_append_only asserts that successive overrides accumulate rather than replace one anoth

---

## Evaluation methodology

`EVALUATION_CONTRACT.md` — ground truth definition, dataset composition,
metrics, and split discipline — was written before any matching code.

- **Dev split, 68 transactions** — all tuning, all threshold and weight changes,
  all experiments.
- **Frozen config** — `app/config.py`, committed.
- **Held-out test, 32 transactions** — run once, after the freeze. Whatever came
  out is what's reported.

Two ground truths are scored separately: pair correctness (is the proposed order
the right one) and decision correctness (is the AUTO/REVIEW/UNMATCHED bucket
right). A system that picks the right order but auto-approves an ambiguous case
is wrong in a way pair accuracy alone would hide.

### Note on the baseline model

The baseline was first attempted on `models/gemini-3.6-flash`, which hit a
20-request daily quota and produced incomplete runs. The valid experiment is
entirely on `models/gemini-3.5-flash-lite`. Both artifacts record the model ID.

---

## Running it

```bash
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
PYTHONPATH=. python app/main.py
```

Open `http://localhost:8000`. Click **Load dev dataset**, or upload your own
transactions and orders CSVs — both need the columns `id, amount, date,
customer_id, reference, description`.

Evaluation:

```bash
PYTHONPATH=. python app/pipeline/evaluate.py
PYTHONPATH=. python evaluation/llm_baseline.py --no-cache --out evaluation/run.json
python evaluation/compare_runs.py run_a.json run_b.json
```

The LLM baseline needs `GEMINI_API_KEY` in `.env`. Responses cache to disk so
runs are reproducible without re-hitting the API; `--no-cache` forces fresh
calls.

---

## Limitations

- Ground truth is synthetic. Real reconciliation data has partial payments,
  batched settlements, refunds, and currency drift — failure modes this dataset
  doesn't contain.
- 68 dev / 32 test transactions. No performance or scale story.
- Single currency, single entity. No FX, no intercompany.
- A near-tie rule is implemented and unit-tested at the boundary, but does not
  fire on this dev set: the multi-candidate records here tie at low scores that
  fall below the floor rather than near the AUTO threshold.
- The score cap described above.
- SQLite on ephemeral hosting — runs do not persist across restarts on the
  deployed instance. Fine for a demo, not for anything else.
- Desktop only. The ledger and detail views are not responsive below ~800px.

## What I'd do next

Fix the score cap properly, with a full re-tune and a fresh held-out run. Build a
dataset containing genuine near-ties above the AUTO threshold so the tie rule is
actually exercised. Test the signal weights against data with partial payments
and batched settlements before trusting any of these numbers outside this
dataset.

---

## Stack

Python · FastAPI · SQLite · React · TypeScript · Vite. Single service — FastAPI
serves both the API and the built frontend.
