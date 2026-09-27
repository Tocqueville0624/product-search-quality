"""Create a local development-error reading queue, without interpreting cases.

Reads only the frozen model's validation predictions and validation partition.
The CSVs are sampling artifacts, not completed human annotations or a random
sample from which to estimate population error rates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import pandas as pd
import pyarrow.dataset as ds


LABELS = ("E", "S", "C", "I")
EVIDENCE_COLUMNS = [
    "query_token_count",
    "title_token_count",
    "query_coverage",
    "token_jaccard",
    "query_in_title",
    "exact_title_match",
    "brand_match",
    "numeric_mismatch",
    "title_missing",
]
MAX_PER_CELL = 4


def create_cases(root: Path) -> dict:
    freeze_path = root / "experiments/frozen_study.json"
    freeze = json.loads(freeze_path.read_text())
    model = freeze["selected_model"]
    if not re.fullmatch(r"[a-z][a-z0-9_]*", model):
        raise ValueError("Expected a plain model name in the frozen study.")
    seed = int(freeze["seed"])
    prediction_path = root / "experiments/runs" / f"{model}_validation.parquet"
    predictions = pd.read_parquet(
        prediction_path, columns=["example_id", "label", "prediction", "p_e"]
    )
    if predictions.example_id.isna().any() or predictions.example_id.duplicated().any():
        raise ValueError("Validation predictions must have unique, non-null example IDs.")
    if not predictions.label.isin(LABELS).all() or not predictions.prediction.isin(LABELS).all():
        raise ValueError("Unknown published or predicted class.")
    if not predictions.p_e.between(0, 1, inclusive="both").all():
        raise ValueError("p_e must be a finite score in [0, 1].")

    errors = predictions.loc[predictions.label != predictions.prediction].copy()
    # SHA-256 creates an order-independent pseudo-random sample within each
    # confusion cell. Labels define these illustrative cells, so this queue
    # must never be mistaken for the label-blind operational review policy.
    errors["sample_hash"] = errors.example_id.map(
        lambda item: hashlib.sha256(f"{seed}:{item}".encode("utf-8")).hexdigest()
    )
    selected = (
        errors.sort_values(["label", "prediction", "sample_hash", "example_id"])
        .groupby(["label", "prediction"], sort=True, group_keys=False)
        .head(MAX_PER_CELL)
        .drop(columns="sample_hash")
        .reset_index(drop=True)
    )
    # Twelve off-diagonal cells times four examples gives at most 48 cases.
    assert len(selected) <= 48

    fields = ["example_id", "query", "product_title", "label", *EVIDENCE_COLUMNS]
    validation = ds.dataset(
        root / "data/processed/features/dataset_split=validation", format="parquet"
    ).to_table(columns=fields).to_pandas()
    if validation.example_id.isna().any() or validation.example_id.duplicated().any():
        raise ValueError("Validation features must have unique, non-null example IDs.")
    cases = selected.merge(
        validation,
        on="example_id",
        how="left",
        validate="one_to_one",
        indicator=True,
        suffixes=("", "_source"),
    )
    if not cases["_merge"].eq("both").all():
        raise ValueError("A selected prediction lacks a validation source row.")
    if not cases.label.eq(cases.label_source).all():
        raise ValueError("Prediction labels do not match the validation source.")
    cases = cases.drop(columns=["_merge", "label_source"])

    public_columns = ["example_id", "label", "prediction", "p_e", *EVIDENCE_COLUMNS]
    public_path = root / "reports/development_case_index.csv"
    public_path.parent.mkdir(parents=True, exist_ok=True)
    cases[public_columns].to_csv(public_path, index=False)

    cases["selection_reason"] = (
        "validation error cell " + cases.label + "→" + cases.prediction
        + "; deterministic sample, at most four per cell"
    )
    cases["human_review_status"] = "pending"
    for column in ["reviewer", "reviewed_at", "reviewer_judgement", "disagreement_reason", "review_notes"]:
        cases[column] = ""
    local_path = root / "experiments/runs/development_cases.csv"
    cases.to_csv(local_path, index=False)
    return {
        "status": "sample_generated_human_review_pending",
        "selected_model": model,
        "seed": seed,
        "validation_error_pairs": len(errors),
        "selected_cases": len(cases),
        "maximum_per_error_cell": MAX_PER_CELL,
        "human_reviews_completed": 0,
        "freeze_sha256": hashlib.sha256(freeze_path.read_bytes()).hexdigest(),
        "public_index": str(public_path.relative_to(root)),
        "local_text_queue": str(local_path.relative_to(root)),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(json.dumps(create_cases(args.root.resolve()), indent=2, ensure_ascii=False))
