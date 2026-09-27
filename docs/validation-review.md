# Validation review

Status: verified offline results. Reviewed 2026-09-27 UTC (2026-09-26 Pacific).

A second Codex agent reviewed the implementation and independently recomputed the headline arithmetic from saved predictions without calling the project's metric functions. This is a reproducibility review within the project, not external certification. No model was retrained or selected using test results during this review.

## Evidence checked

- SHA-256 values matched for both raw source files, all 8 frozen Python source files, all 25 recorded model/processed-data artifacts, and the study configuration. The current artifact file set also matched the frozen inventory.
- The exposure record's freeze hash matched [the frozen study](../experiments/frozen_study.json). Its timestamps show freeze at `03:16:30 UTC`, test exposure at `03:17:07 UTC`, and results afterward. The implementation prevents ordinary retraining after test exposure.
- Saved test predictions contained exactly the official US large-version test's 425,762 example IDs, with labels matching individually. They cover 22,458 queries.
- Train, validation and test query IDs and normalized query texts were disjoint. All three query-split hashes were independently recomputed and matched. One overlapping official training query, containing 3 rows, was excluded; official test membership was preserved.
- The final split has 1,113,987 training, 279,073 validation and 425,762 test pairs. The data audit covers 1,818,825 US input pairs and a row-preserving product join. The recorded deterministic small-sample transformation covered 1,944 pairs before the full transformation.
- Review ordering uses predicted-Exact membership, ascending model score, and example ID only for deterministic ties. Published labels score an already selected queue. No test labels, query/product IDs or split flags occur among the 17 model features.

References: [data audit](../reports/data_audit.json), [small-sample check](../reports/sample_smoke.json), [test results](../reports/test_metrics.json), [exposure record](../experiments/test_exposure.json).

## Confirmed numbers and denominators

| Quantity | Verified value | Denominator or interpretation |
| --- | ---: | --- |
| Test macro-F1 | 0.333392 | Unweighted mean of the four class F1 values |
| Majority-baseline macro-F1 | 0.197229 | Same test pairs and fixed four labels |
| Predicted-Exact pool | 199,989 pairs | 46.9720% of all test pairs |
| Published non-Exact labels in this pool | 39,729 | Pool error rate: 19.8656% |
| 10% review budget | 19,998 pairs | Floor of 10% of the pool, not all test pairs |
| Priority queue's errors | 6,575 | 32.8783% of reviewed pairs |
| Uniform random expectation | 3,972.7212 errors | 19.8656% expected yield at the identical item budget |
| Pool-error recall | 16.5496% | 6,575 / 39,729 |
| Unreviewed pool error rate | 18.4198% | 33,154 / 179,991 remaining pairs |
| Complement prediction precision | 4.1741% | 2,425 correct / 58,096 predicted C pairs |

The random count is an analytical expectation, not one observed integer sample. The priority queue's published error labels comprise 4,785 Substitute, 447 Complement and 1,343 Irrelevant pairs. These error types need not have equal operational cost.

The recorded 300-replicate query-cluster bootstrap gives a 95% percentile interval of 31.86–34.01% for priority yield and +12.11 to +14.01 percentage points for yield minus random expectation (point difference: +13.01 points). It resamples whole queries with a fixed fitted model. It does not cover model retraining, label uncertainty, future traffic shifts or online business impact. Random-policy sampling percentiles are a separate concept, not this confidence interval.

## Decision and limits

The class-weighted model was selected by validation macro-F1: 0.333977 versus 0.259277 for the unweighted candidate. Its scores are not calibrated probabilities under natural class prevalence. Its higher macro-F1 comes with weaker overall accuracy: 48.82% on test versus 65.14% for the majority baseline. Complement precision is particularly poor. This evidence supports an offline queue-prioritization experiment; it does not justify automatic relabeling or production search ranking.

The same-model, same-pool review comparison is valid. Cross-model review yields use different pools and cannot establish which model is best for the entire operational objective. No review times, human corrections, revenue, CTR, conversions, cost savings or online lift were observed. The project collected no new human labels; case exports are material for future review, not completed human validation.

The work provides concrete portfolio evidence of local PySpark/Spark SQL, data provenance, leakage controls, ML tradeoffs and a measurable offline operations question. It does not demonstrate AWS/distributed-cluster experience, a new algorithm, a production-ready relevance model, or guaranteed hiring benefit.

Minor documentation discrepancy: the frozen slice description says “1–2” query tokens, while executable code and results say “0–2.” Independently confirmed zero test pairs have zero tokens, so reported test slice values are unaffected. The original freeze is preserved rather than silently edited after evaluation.

Further improvements motivated by these test results require a fresh holdout for new confirmatory claims; reuse of this test must be labeled exploratory.

## Publication addendum

Commit `ee8b6ba` preserves all eight source files exactly as frozen and reviewed above. After that commit, the obsolete initialization-only package docstring in `src/search_quality/__init__.py` was corrected. No executable logic or metrics changed. Old/new hashes and the baseline commit are recorded in [post-freeze-documentation.json](../experiments/post-freeze-documentation.json); the original frozen study was not rewritten. A separate complete technical reproduction matched classification, review and bootstrap outputs exactly ([reproduction check](../reports/reproduction_check.json)).
