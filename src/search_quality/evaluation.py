"""Independent offline ESCI metrics and query-cluster uncertainty.

Rows are published query-product judgements, never traffic or human work hours.
Selection uses predictions/probabilities only; labels score the resulting queue.
"""

from __future__ import annotations

import math
from typing import Iterable

import numpy as np
import pandas as pd

LABELS = ("E", "S", "C", "I")
_LABEL_INDEX = {label: index for index, label in enumerate(LABELS)}


def _validate(df: pd.DataFrame, *, review: bool = False, groups: bool = False) -> None:
    required = {"label", "prediction"}
    if review:
        required |= {"example_id", "p_e"}
    if groups:
        required.add("query_id")
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing evaluation columns: {sorted(missing)}")
    for column in ("label", "prediction"):
        if not df[column].isin(LABELS).all():
            raise ValueError(f"{column} must contain only {LABELS}, without missing values")
    if groups and df["query_id"].isna().any():
        raise ValueError("query_id must not be missing")
    if review:
        if df["example_id"].isna().any() or df["example_id"].duplicated().any():
            raise ValueError("example_id must be nonmissing and unique")
        probabilities = df["p_e"].to_numpy(dtype=float)
        if not (np.isfinite(probabilities).all() and ((probabilities >= 0) & (probabilities <= 1)).all()):
            raise ValueError("p_e must contain finite probabilities in [0, 1]")


def _ratio(numerator: float, denominator: float) -> float | None:
    return float(numerator / denominator) if denominator else None


def _confusion(df: pd.DataFrame) -> np.ndarray:
    actual = df["label"].map(_LABEL_INDEX).to_numpy(dtype=np.int64)
    predicted = df["prediction"].map(_LABEL_INDEX).to_numpy(dtype=np.int64)
    return np.bincount(actual * 4 + predicted, minlength=16).reshape(4, 4)


def _macro_f1(matrix: np.ndarray) -> float | None:
    if matrix.sum() == 0:
        return None
    denominator = matrix.sum(axis=0) + matrix.sum(axis=1)
    scores = np.divide(2.0 * matrix.diagonal(), denominator, out=np.zeros(4), where=denominator != 0)
    return float(scores.mean())


def classification_metrics(df: pd.DataFrame) -> dict:
    """Report fixed-label macro F1, not Spark's support-weighted ``f1``.

    Precision/recall with no denominator are None. Per-class F1 is 0 if
    its denominator is 0; macro F1 always averages all four classes, and
    is None for an empty dataset. Confusion rows are actual, columns predicted.
    """
    _validate(df)
    matrix = _confusion(df)
    size = len(df)
    by_class = {}
    for index, label in enumerate(LABELS):
        support = int(matrix[index].sum())
        predicted = int(matrix[:, index].sum())
        correct = int(matrix[index, index])
        by_class[label] = {
            "support": support,
            "predicted": predicted,
            "precision": _ratio(correct, predicted),
            "recall": _ratio(correct, support),
            "f1": _ratio(2 * correct, support + predicted) if support + predicted else 0.0,
        }
    pool_size = int(matrix[:, 0].sum())
    errors = int(matrix[1:, 0].sum())
    return {
        "n_rows": size,
        "labels": list(LABELS),
        "accuracy": _ratio(int(matrix.trace()), size),
        "macro_f1": _macro_f1(matrix),
        "per_class": by_class,
        "confusion_matrix": matrix.tolist(),
        "confusion_orientation": "rows=published label; columns=prediction",
        "predicted_exact": {
            "n_rows": pool_size,
            "coverage": _ratio(pool_size, size),
            "n_errors": errors,
            "error_rate": _ratio(errors, pool_size),
            "errors_by_label": {label: int(matrix[index, 0]) for index, label in enumerate(LABELS) if label != "E"},
        },
        "zero_division_policy": "undefined precision/recall=None; absent-class F1=0; empty macro F1=None",
    }


def _budget_count(pool_size: int, fraction: float) -> int:
    if not math.isfinite(fraction) or not 0 <= fraction <= 1:
        raise ValueError("Budget fractions must be finite and in [0, 1]")
    return math.floor(pool_size * fraction)


def _pool(df: pd.DataFrame) -> pd.DataFrame:
    # Neither truth nor any label-derived field appears in this ordering.
    return df.loc[df["prediction"].eq("E")].sort_values(["p_e", "example_id"], kind="mergesort")


def _review_score(pool_size: int, pool_errors: int, reviewed: int, found: float) -> dict:
    return {
        "n_reviewed": reviewed,
        "n_errors_found": found,
        "audit_yield": _ratio(found, reviewed),
        "error_recall": _ratio(found, pool_errors) if reviewed else None,
        "n_remaining": pool_size - reviewed,
        "n_remaining_errors": pool_errors - found,
        "remaining_error_rate": _ratio(pool_errors - found, pool_size - reviewed),
    }


def review_metrics(
    df: pd.DataFrame,
    budgets: Iterable[float] = (0.05, 0.10),
    seed: int = 20260926,
    repeats: int = 100,
) -> dict:
    """Equal-item-budget queues within one model's predicted-Exact pool.

    Random draws are hypergeometric: exactly the error-count distribution of
    uniform sampling without replacement, without allocating random queues.
    Their percentile range is random-policy variability, NOT a confidence
    interval for performance on future data. Expected values are analytical.
    """
    _validate(df, review=True)
    if repeats < 1:
        raise ValueError("repeats must be positive")
    pool = _pool(df)
    size = len(pool)
    errors = int(pool["label"].ne("E").sum())
    rng = np.random.default_rng(seed)
    results = []
    for budget in budgets:
        fraction = float(budget)
        count = _budget_count(size, fraction)
        selected = pool.iloc[:count]
        found = int(selected["label"].ne("E").sum())
        confidence = _review_score(size, errors, count, found)
        confidence["errors_by_label"] = {label: int(selected["label"].eq(label).sum()) for label in LABELS[1:]}
        expected_found = count * errors / size if size else 0.0
        expected = _review_score(size, errors, count, expected_found)
        expected["errors_by_label"] = {
            label: count * int(pool["label"].eq(label).sum()) / size if size else 0.0 for label in LABELS[1:]
        }
        if count:
            draws = rng.hypergeometric(errors, size - errors, count, size=repeats)
            yields = draws / count
            variability = {
                "repeats": repeats,
                "audit_yield_mean": float(yields.mean()),
                "audit_yield_p025": float(np.quantile(yields, 0.025)),
                "audit_yield_p975": float(np.quantile(yields, 0.975)),
            }
        else:
            variability = {"repeats": 0, "audit_yield_mean": None, "audit_yield_p025": None, "audit_yield_p975": None}
        results.append({
            "budget_fraction": fraction,
            "n_reviewed": count,
            "uncertainty_priority": confidence,
            "uniform_random": {"expected": expected, "sampling_variability": variability},
        })
    return {
        "pool_size": size,
        "pool_errors": errors,
        "pool_error_rate": _ratio(errors, size),
        "budget_rounding": "floor(pool_size * fraction); zero items gives no audit estimate",
        "priority_order": "ascending p_e, then ascending example_id; labels excluded",
        "seed": seed,
        "budgets": results,
    }


def _weighted_yield(pool_group: np.ndarray, is_error: np.ndarray, weights: np.ndarray, budget: float) -> tuple[float | None, float | None]:
    """Evaluate a queue of repeated query clusters without expanding rows."""
    row_weights = weights[pool_group]
    size = int(row_weights.sum())
    count = _budget_count(size, budget)
    if count == 0:
        return None, None
    preceding = np.cumsum(row_weights) - row_weights
    selected_weights = np.minimum(row_weights, np.maximum(count - preceding, 0))
    found = float(selected_weights @ is_error)
    return found / count, float(row_weights @ is_error) / size


def _interval(point: float | None, values: list[float], confidence: float) -> dict:
    alpha = (1 - confidence) / 2
    return {
        "point": point,
        "low": float(np.quantile(values, alpha)) if values else None,
        "high": float(np.quantile(values, 1 - alpha)) if values else None,
        "n_valid": len(values),
    }


def query_bootstrap(
    df: pd.DataFrame,
    budget: float = 0.10,
    n_bootstrap: int = 200,
    seed: int = 20260926,
    confidence: float = 0.95,
) -> dict:
    """Percentile intervals from resampling whole query groups with replacement.

    Each replicate samples G queries from G observed queries. All rows of a
    sampled query get the same multiplicity. Macro F1 remains pair weighted;
    the *resampling unit* is a query. Review budgets are recomputed per replicate.
    Model weights remain fixed: intervals do not cover retraining uncertainty.
    """
    _validate(df, review=True, groups=True)
    _budget_count(0, budget)
    if n_bootstrap < 1 or not 0 < confidence < 1:
        raise ValueError("n_bootstrap must be positive and confidence must be in (0, 1)")
    group_codes, groups = pd.factorize(df["query_id"], sort=True)
    n_groups = len(groups)
    actual = df["label"].map(_LABEL_INDEX).to_numpy(dtype=np.int64)
    predicted = df["prediction"].map(_LABEL_INDEX).to_numpy(dtype=np.int64)
    per_query = np.zeros((n_groups, 16), dtype=np.int64)
    np.add.at(per_query, (group_codes, actual * 4 + predicted), 1)
    # Attach group codes positionally so arbitrary/duplicate DataFrame indexes
    # cannot corrupt alignment. example_id remains the deterministic tie breaker.
    coded = df.assign(_bootstrap_group=group_codes)
    pool = _pool(coded)
    pool_group = pool["_bootstrap_group"].to_numpy(dtype=np.int64)
    is_error = pool["label"].ne("E").to_numpy(dtype=np.int64)
    point_yield, point_random = _weighted_yield(pool_group, is_error, np.ones(n_groups, dtype=np.int64), budget)
    point_f1 = _macro_f1(per_query.sum(axis=0).reshape(4, 4))
    f1_values, yield_values, random_values, differences = [], [], [], []
    rng = np.random.default_rng(seed)
    # A one-query dataset has no information about variation across queries.
    if n_groups >= 2:
        for _ in range(n_bootstrap):
            sampled = rng.integers(0, n_groups, size=n_groups)
            weights = np.bincount(sampled, minlength=n_groups)
            matrix = (weights @ per_query).reshape(4, 4)
            f1_values.append(_macro_f1(matrix))
            priority_yield, random_yield = _weighted_yield(pool_group, is_error, weights, budget)
            if priority_yield is not None:
                yield_values.append(priority_yield)
                random_values.append(random_yield)
                differences.append(priority_yield - random_yield)
    point_difference = point_yield - point_random if point_yield is not None else None
    return {
        "method": "query-cluster percentile bootstrap; fixed fitted model",
        "n_queries": n_groups,
        "n_rows": len(df),
        "n_bootstrap_requested": n_bootstrap,
        "seed": seed,
        "confidence": confidence,
        "budget_fraction": budget,
        "status": "computed" if n_groups >= 2 else "insufficient_query_groups",
        "macro_f1": _interval(point_f1, f1_values, confidence),
        "audit_yield": _interval(point_yield, yield_values, confidence),
        "random_expected_yield": _interval(point_random, random_values, confidence),
        "audit_yield_minus_random": _interval(point_difference, differences, confidence),
        "limitations": "Observed query clusters only; no retraining or label-uncertainty coverage; not online impact.",
    }
