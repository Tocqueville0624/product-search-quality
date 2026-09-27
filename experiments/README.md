# Experiments

- `frozen_study.json`: development selection, fixed settings, raw-data provenance, query hashes, source/model/feature artifact hashes, runtime and timing. It was written before test evaluation.
- `test_exposure.json`: the immutable start-of-test marker and freeze SHA. It prevents silent retraining after exposure.
- `runs/`: local predictions, development text queue and Spark event logs, excluded from Git.

The first implementation had no commit yet; its exact source contents are identified by SHA-256. The public repository commit preserves those source files. Stage durations are observed local measurements, exclude downloads and some startup time, and are not a Spark speedup comparison.

To technically reproduce the frozen design, use `scripts/run_study.py --name <new-name>`; it keeps new outputs in ignored `.reproduction/` and does not overwrite these reference artifacts. Each new run independently freezes before evaluating. Repetition is not independent scientific validation, and tuning from published test errors requires a fresh holdout for confirmatory claims.

The `test_status = "unopened"` setting in the frozen study configuration describes its pre-evaluation design state. The actual reference test is now exposed, as recorded by `test_exposure.json`, final metrics, and `docs/STATUS.md`; do not infer current exposure from that immutable config string.
