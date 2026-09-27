# Product Search Quality — Agent Instructions

## Mission
- Build an independent, Codex-assisted portfolio project for general/product Data Scientist applications in a 2–4 week first iteration.
- Use Amazon ESCI US English query–product pairs; demonstrate PySpark/Spark SQL, explainable ML, valid evaluation, and product judgment.
- Core question: how well can we classify relevance, and prioritize false Exact predictions for a fixed manual-review budget?
- Read `docs/STATUS.md`, `docs/project-brief.md`, and `docs/evaluation-plan.md` before implementing; update status after meaningful work.

## Package Manager and Commands
- Use `uv`, project-local `.venv`, and committed `uv.lock`; verified Python 3.11, Java 17, PySpark 3.5.7. See README for setup.
- Reproduce via `uv run python scripts/run_study.py --name <new-name>`; preserve committed results and test-exposure records. No cloud resources are needed.
- Tests: set Java as in README, then `uv run python -m pytest -q` (23 focused checks). Figures/PDF: scripts/build_reports.py and scripts/build_guide_pdf.py; never document imagined success.

## Attribution and Independent Work
- Read `docs/prior-art.md` and `THIRD_PARTY_NOTICES.md`; the ESCI task, dataset, standard models, and Spark processing are established prior work.
- Implement this project's analysis and pipeline independently; do not clone a competitor project and present it as original work.
- Cite data, methods, and substantive inspirations. For copied/adapted code, record source URL, revision, license, destination, and changes before reuse.
- Keep required upstream LICENSE/NOTICE material when redistributing covered material; public visibility alone is not permission to reuse code.
- Never claim a novel algorithm, first-of-its-kind system, competition participation, Amazon employment, or endorsement.
- Keep employer/client prompts, labels, rubrics, outputs, and confidential material out of this project.

## Data and Evaluation
- Follow `docs/data-contract.md`; count actual downloaded/filtered rows and record source revision, SHA-256, schema, exclusions, and join cardinality.
- Join on `(product_locale, product_id)`; detect duplicate keys and unmatched products before modeling.
- Preserve official test membership. Derive validation only from official training queries; fit all learned preprocessing on training only.
- Audit query IDs, normalized query text, and exact duplicate pairs across splits; freeze a documented overlap policy before training.
- Never use test labels, IDs, split flags, or label-derived lookup tables as model features or review-selection signals.
- Tune models, slice definitions, confidence thresholds, and review policies on development data. Freeze them before final test evaluation.
- After inspecting test errors, treat further improvements as exploratory on that test and obtain a fresh holdout for new confirmatory claims.
- Compare review policies on the same model's predicted-Exact pool at equal item budgets; use hidden labels only to score the selected items.
- Report denominators, per-class results, query-group uncertainty, and limitations; keep published labels and human disagreements separate.
- Never manufacture metric gains, business lift, data volume, cloud runs, human agreement, or performance advantages for Spark.

## Implementation Scope
- Start with a small deterministic query sample, a majority baseline, lexical pair features, and a simple classifier; scale after correctness checks.
- Use PySpark for real joins, quality checks, aggregation, and feature preparation; SQL artifacts must answer concrete analysis questions.
- Keep notebooks for exploration and reusable logic in `src/search_quality/`; add focused checks for joins, splits, leakage, and metrics as implemented.
- Prefer one interpretable improvement at a time; defer large ensembles, vector databases, a full search service, and extensive UI work.
- Local Spark is local execution. Claim distributed/cloud experience only with actual worker/executor and job evidence.
- Continue authorized local work autonomously; before paid cloud/API runs or public deployment, resolve budget or publication choices only if not already authorized.

## Results and Iteration
- Keep raw data, model binaries, caches, credentials, and detailed run outputs out of Git; track small manifests/configs and verified summary reports.
- Record experiment question, data revision, split hashes, seed, code revision, environment, actual compute, metrics, and decision in `experiments/`.
- Preserve negative results. Success means a defensible finding and reproducible workflow, not beating a leaderboard.
- Explain decisions to the user in Chinese; maintain a concise English README for eventual portfolio use.
- Teach the user to explain the observation unit, labels, split, baseline, metric, Spark work, and offline/online distinction.
- Mark every result as planned, running, verified, or exploratory; update `docs/STATUS.md` with the next concrete step and remaining limitations.

## Commit Attribution
- For AI-authored commits, include `Co-Authored-By` using the actual model name and configured agent attribution; never invent a person's identity or email.
- Initialization does not require a commit or remote publication.
