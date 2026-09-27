# Decision memo: prioritizing search-quality reviews

**Status: verified offline study; proposed operational pilot has not run.**

## Recommendation

Pilot a queue that reviews the lowest model scores among pairs predicted Exact. Maintain a separate uniform random audit to estimate the overall error rate. Use human decisions to determine corrections. The current classifier is not suitable for automatic relevance decisions.

## Operational question

A quality team has a fixed capacity measured in query–product pairs inspected. Can a simple relevance model direct that capacity toward more questionable Exact predictions?

The published ESCI labels distinguish Exact (E), Substitute (S), Complement (C), and Irrelevant (I). The queue contains model predictions of E; a model error is a published S, C, or I label. This is model-error triage, not proof that an upstream human annotation is wrong.

## Evidence

The official US test set contains 425,762 pairs across 22,458 queries. The frozen class-weighted logistic model predicted E for 199,989 pairs (46.97% coverage); 39,729 of these have non-E labels (19.87%). Selection uses ascending E score with example ID as a deterministic tie-breaker. Labels only score the selected rows.

| Budget within this pool | Inspections | Priority errors found | Random expected errors | Priority audit yield |
| --- | ---: | ---: | ---: | ---: |
| 5% | 9,999 | 3,386 | 1,986.4 | 33.86% |
| 10% | 19,998 | 6,575 | 3,972.7 | 32.88% |

At 10%, priority finds about **2,602 additional labeled errors** versus uniform random expectation, using the same number of inspections. Yield is **1.655 times** the random expectation. The paired yield difference is +13.01 percentage points, with a 95% query-cluster bootstrap interval of 12.11–14.01 pp. Intervals hold the fitted model fixed and do not cover retraining, label validity, or changes in live traffic.

The 6,575 flagged errors include **4,785 Substitutes, 447 Complements, and 1,343 Irrelevant pairs**. A substitute may still be useful to a shopper. Treating all three errors equally is an evaluation convention, not a claim about customer harm or business cost.

## What this changes operationally

1. **Create an audit queue**, using the score as a ranking signal. Class weighting means the score is not a calibrated probability of correctness.
2. **Keep a random measurement stream.** The priority queue is intentionally error enriched; its 32.88% yield cannot estimate the full pool's error rate.
3. **Record adjudicated error type and action.** Inspectors should distinguish useful alternatives, accessories, incompatibility, and clearly irrelevant products before considering interventions.
4. **Start with capacity, not a revenue promise.** The simulation fixes the number of items inspected. It contains no measured inspection time, salary, purchase, or customer-retention outcome.

## Why automatic deployment is premature

- Macro-F1 is 0.3334 (95% query interval 0.3302–0.3367), versus a majority baseline of 0.1972. Accuracy decreases from 65.14% to 48.82% after the model is selected for balanced class performance.
- Complement precision is 4.17%. Lexical overlap does not reliably distinguish an accessory from the requested product.
- The 10% review catches only 16.55% of errors inside the Exact pool. **33,154 errors remain among 179,991 uninspected pairs** (18.42%). Errors outside the pool are not addressed.
- Longer-query slices have higher observed Exact-pool error rates (22.22% for 3+ tokens vs 13.84% for 0–2). This is descriptive, not a causal claim or a validated new selection rule. Slice checks do not adjust for all query/product differences.
- The benchmark provides selected candidate pairs, not live query frequencies or a complete product catalogue. No temporal or online transfer has been established.

## Proposed validation before use

**Human review pilot:** draw separate, equal-size random and priority samples from the same frozen pool; hide the selection arm and model score from reviewers where practical; use an adjudication rubric with independent overlap review. Measure confirmed errors per inspected pair, disagreements, inspection time, and error composition. Neither the rubric nor human agreement has been evaluated in this MVP.

**If ranking changes follow:** design a separate online experiment with a stable user-level assignment, a prespecified search-success measure from actual logs, and latency, abandonment, and harmful-result guardrails. Define sample size and minimum detectable effect only after obtaining baseline rates and repeated-user variation. This public dataset cannot supply them.

## Traceability

[Final metrics](test_metrics.json) · [Model selection](validation_metrics.json) · [Data audit](data_audit.json) · [Frozen study](../experiments/frozen_study.json) · [Independent verification](../docs/validation-review.md)

All findings were computed locally using public data. No customers were exposed, no production system was changed, and no business lift was measured.
