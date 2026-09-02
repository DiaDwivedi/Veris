# Evaluation Contract

This contract defines the ground rules for evaluating the AI Finance Controller matching engine.
No dataset generation or algorithm development should begin until these constraints are acknowledged.

## Rules of Engagement

1. **Deterministic Logic**: The matching engine must use explicit, deterministic rules (e.g., date ranges, exact amount matches, known reference formats).
2. **No Generative AI for Matching**: LLMs must never be used to decide if two records are a match.
3. **Immutability**: The system must not move money, settle invoices directly, or mutate original financial records.
4. **Conservation of Records**: Unmatched records must not be discarded. Every ingested record must end up in a `ReconciliationResult`.

## Key Metrics

* **False Positive Rate for AUTO matches (Critical)**: Target as close to 0% as achievable on the held-out test set. Any AUTO-match false positive found during evaluation is treated as a launch-blocking bug, not an acceptable error rate. The reported rate is measured on the held-out test set and must not be presented as a guarantee.

* **Overall Candidate Recall (Primary Recall Metric)**: Of all records with a known ground-truth match, the percentage for which the system identifies a plausible candidate and routes the record to either AUTO or REVIEW. A correct match routed to REVIEW therefore counts as successfully identified for overall candidate recall.

* **AUTO-Match Recall (Secondary Diagnostic)**: Of all records with a known ground-truth match, the percentage that are ultimately routed to AUTO. This metric may be lower because the system intentionally prioritizes safety over aggressive automation.

* **Auditability**: 100% of generated MatchCandidates must contain a transparent `audit_trail` listing the rules that were triggered.

## Reported Metrics

* AUTO precision
* Overall candidate recall
* AUTO-match recall
* AUTO rate
* REVIEW rate
* UNMATCHED rate

## Core Safety Principle

When evidence is insufficient for safe automatic reconciliation, REVIEW is preferred over an incorrect AUTO decision.

## Score Interpretation

Confidence is treated as a deterministic rule-based score, not a statistical probability.

Initial configurable thresholds:

- >= 90 → AUTO
- 70 <= score < 90 → REVIEW
- < 70 → UNMATCHED

These are initial policy thresholds and may be tuned using the development set. Once held-out test-set evaluation begins, thresholds must not be adjusted based on test-set results.