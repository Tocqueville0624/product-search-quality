# Third-party sources and attribution

## Original implementation

The original project implementation and documentation are MIT licensed (see `LICENSE`). Codex assisted with implementation, analysis, review, and writing. No competitor repository, notebook, or model implementation was copied. Standard algorithms and the existing benchmark are not claimed as novel.

## Amazon ESCI data

- Source: [amazon-science/esci-data](https://github.com/amazon-science/esci-data).
- Exact revision: `7916cdf6ab75a462e77f20ab40428a10923998d5`.
- Paper: [Reddy et al. (2022), Shopping Queries Dataset](https://arxiv.org/abs/2206.06588).
- License: Apache-2.0; preserved at [references/upstream/ESCI-LICENSE](references/upstream/ESCI-LICENSE).
- Original notice: preserved verbatim at [references/upstream/ESCI-NOTICE](references/upstream/ESCI-NOTICE).
- Downloaded originals: `data/raw/shopping_queries_dataset_examples.parquet` and `data/raw/shopping_queries_dataset_products.parquet`; neither is committed or redistributed in this repository.
- File SHA-256, sizes, schemas, rows and source URLs: [source manifest](data/manifests/source.json). Checksums match upstream Git LFS pointers at the fixed revision.
- Processing: filter US large-version pairs; join products; remove 3 overlapping training rows; derive development splits and lexical features. Raw files are not edited. Public reports contain aggregate analysis and a small ID-only development case index.

This independent project is not affiliated with, endorsed by, or employed by Amazon. It does not claim participation in the original challenge. Published relevance judgments may contain disagreement and do not measure business impact.

## Libraries and runtime

Dependency versions are fixed in `uv.lock`. PySpark, NumPy, pandas, PyArrow, matplotlib and the documentation/test libraries retain their own licenses. Installed libraries, JDK binaries and their files are not committed. The Java helper downloads Eclipse Temurin 17 from the vendor API and verifies its provided SHA-256; vendor release metadata remains in the ignored local runtime directory.

The optional local PDF generator uses an installed Chinese font (or a user-specified Unicode TrueType font). No font files or generated PDFs are redistributed through this repository.

## Methods and inspiration

[Prior-art research](docs/prior-art.md) documents similar public work and the independent contribution boundary. [Learning resources](docs/learning-resources.md) cite primary documentation for the methods used. Reviewing a repository is not evidence of code incorporation or permission to copy it.

The post-implementation prior-art follow-up adds uncertainty sampling (Settles, 2009), selective classification (Geifman and El-Yaniv, 2017), and PRECISE (Divekar and Majumder, 2026) as method context or related work. These sources were added after the MVP; no code or results from them were incorporated, and their algorithms are not claimed as this project's invention.

If substantive code is later copied or adapted, record its URL, revision, license, destination, purpose and changes here, and retain required attribution close to the adapted code. Public visibility alone is not a reuse license. Employer/client prompts, labels, rubrics and confidential artifacts are excluded.
