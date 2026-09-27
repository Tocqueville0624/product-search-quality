"""Hand-computed synthetic checks; no benchmark data or training required."""

import math

import numpy as np
import pandas as pd
import pytest

from search_quality.evaluation import (
    _weighted_yield,
    classification_metrics,
    query_bootstrap,
    review_metrics,
)


def frame(labels, predictions=None, probabilities=None, queries=None):
    n = len(labels)
    return pd.DataFrame({
        "example_id": np.arange(n),
        "query_id": queries if queries is not None else np.arange(n),
        "label": labels,
        "prediction": predictions if predictions is not None else ["E"] * n,
        "p_e": probabilities if probabilities is not None else np.linspace(0.3, 0.9, n),
    })


def test_fixed_label_macro_is_not_accuracy_or_weighted_f1():
    result = classification_metrics(frame(["E", "E", "S", "C"]))
    assert result["accuracy"] == 0.5
    assert result["per_class"]["E"]["f1"] == pytest.approx(2 / 3)
    assert result["macro_f1"] == pytest.approx(1 / 6)
    assert result["per_class"]["I"]["recall"] is None
    assert result["per_class"]["I"]["f1"] == 0
    assert result["confusion_matrix"] == [[2, 0, 0, 0], [1, 0, 0, 0], [1, 0, 0, 0], [0, 0, 0, 0]]
    assert result["predicted_exact"]["coverage"] == 1
    assert result["predicted_exact"]["error_rate"] == 0.5


def test_review_uses_equal_budgets_and_correct_denominators():
    data = frame(["S", "I", "E", "E", "E", "C"], ["E"] * 5 + ["C"])
    result = review_metrics(data, budgets=(0.4,), repeats=200)
    budget = result["budgets"][0]
    assert result["pool_size"] == 5
    assert result["pool_errors"] == 2
    priority = budget["uncertainty_priority"]
    random = budget["uniform_random"]["expected"]
    assert priority["n_reviewed"] == random["n_reviewed"] == 2
    assert priority["audit_yield"] == priority["error_recall"] == 1
    assert priority["remaining_error_rate"] == 0
    assert priority["errors_by_label"] == {"S": 1, "C": 0, "I": 1}
    assert random["audit_yield"] == pytest.approx(0.4)
    assert random["error_recall"] == pytest.approx(0.4)
    assert random["remaining_error_rate"] == pytest.approx(0.4)


def test_selection_does_not_depend_on_labels_and_ties_use_example_id():
    data = frame(["S", "E", "E", "I"], probabilities=[0.5] * 4)
    shuffled = data.iloc[[3, 2, 0, 1]]
    first = review_metrics(shuffled, budgets=(0.25,))["budgets"][0]["uncertainty_priority"]
    assert first["errors_by_label"]["S"] == 1
    # Change only labels. The same first example must still be selected.
    changed = shuffled.assign(label=["S", "S", "E", "S"])
    second = review_metrics(changed, budgets=(0.25,))["budgets"][0]["uncertainty_priority"]
    assert second["n_errors_found"] == 0


def test_empty_and_zero_budget_are_not_perfect_scores():
    empty = frame([])
    assert classification_metrics(empty)["macro_f1"] is None
    assert review_metrics(empty)["pool_error_rate"] is None
    assert query_bootstrap(empty)["macro_f1"]["low"] is None
    data = frame(["E", "E"])
    zero = review_metrics(data, budgets=(0.1,))["budgets"][0]["uncertainty_priority"]
    assert zero["n_reviewed"] == 0
    assert zero["audit_yield"] is None
    assert zero["error_recall"] is None
    full = review_metrics(data, budgets=(1.0,))["budgets"][0]["uncertainty_priority"]
    assert full["audit_yield"] == 0
    assert full["error_recall"] is None
    assert full["remaining_error_rate"] is None


def test_floor_rounding_and_random_repeatability():
    data = frame(["S", "E", "I", "E", "E", "C", "E"])
    first = review_metrics(data, budgets=(0.25,), seed=3)
    assert first["budgets"][0]["n_reviewed"] == 1
    assert first == review_metrics(data, budgets=(0.25,), seed=3)


def test_weighted_query_queue_matches_expanded_sample():
    group = np.array([0, 1, 0, 2, 1])
    errors = np.array([1, 0, 0, 1, 1])
    weights = np.array([2, 0, 3])
    expanded_errors = np.repeat(errors, weights[group])
    k = math.floor(len(expanded_errors) * 0.6)
    priority, random = _weighted_yield(group, errors, weights, 0.6)
    assert priority == expanded_errors[:k].mean()
    assert random == expanded_errors.mean()


def test_bootstrap_samples_whole_query_groups():
    # Query A has 20 always-correct E pairs; B has 20 always-wrong S pairs.
    # Whole-query draws yield only F1 = 0, 1/6, or 1/4, hence the wide interval.
    data = frame(["E"] * 20 + ["S"] * 20, queries=["a"] * 20 + ["b"] * 20)
    data.index = [0] * len(data)  # index alignment must not change group membership
    result = query_bootstrap(data, budget=0.5, n_bootstrap=200, seed=5)
    assert result["n_queries"] == 2
    assert result["macro_f1"]["point"] == pytest.approx(1 / 6)
    assert result["macro_f1"]["low"] == 0
    assert result["macro_f1"]["high"] == 0.25
    assert result["audit_yield"]["low"] == 0
    assert result["audit_yield"]["high"] == 1
    assert result == query_bootstrap(data, budget=0.5, n_bootstrap=200, seed=5)


def test_one_query_has_no_fake_confidence_interval():
    data = frame(["E", "S"], queries=["same", "same"])
    result = query_bootstrap(data, budget=0.5)
    assert result["status"] == "insufficient_query_groups"
    assert result["macro_f1"]["point"] is not None
    assert result["macro_f1"]["low"] is None
    assert result["macro_f1"]["n_valid"] == 0


@pytest.mark.parametrize("column,value", [("label", "X"), ("prediction", None), ("p_e", np.nan), ("p_e", 1.1), ("query_id", None)])
def test_invalid_inputs_rejected(column, value):
    data = frame(["E", "S"])
    data.loc[0, column] = value
    with pytest.raises(ValueError):
        query_bootstrap(data)


def test_duplicate_ids_rejected():
    data = frame(["E", "S"])
    data["example_id"] = 1
    with pytest.raises(ValueError, match="unique"):
        review_metrics(data)
