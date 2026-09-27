# Focused checks

23 tests cover native Spark lexical features (6), grouped data splitting and overlap removal (3), and classification/review/bootstrap metrics (14). Test data is synthetic and contains no private material.

Follow README to set Java 17, then run `uv run python -m pytest -q`. Spark tests share one small `local[1]` session and require local Python–Java socket communication. No network service, AWS account, raw dataset, or paid API is needed for the tests.

The separate full reproduction and official-data/hash checks are recorded in `docs/validation-review.md` and `reports/`.
