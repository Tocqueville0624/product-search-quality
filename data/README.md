# Data

Official source: https://github.com/amazon-science/esci-data, pinned to `7916cdf6ab75a462e77f20ab40428a10923998d5`.

`manifests/source.json` records verified upstream SHA-256, row counts, schemas and URLs. The acquisition module checks both new downloads and cached files against the immutable upstream Git LFS checksums.

- `raw/`: original Parquet, ignored by Git.
- `processed/`: derived features partitioned by train/validation/test, ignored by Git.
- `manifests/`: small provenance files, committed.

Use the repository README reproduction command. Read `docs/data-contract.md` and `reports/data_audit.json` for actual filtering, split policy and join checks. Data retains its upstream Apache-2.0 terms; raw files are not redistributed here.
