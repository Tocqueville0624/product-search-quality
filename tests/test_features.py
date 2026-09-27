"""Small synthetic checks of feature meaning and independence from labels."""

import math

import pytest
from pyspark.sql import functions as F

from search_quality.features import FEATURE_COLUMNS, build_features


def _frame(spark, rows):
    return spark.createDataFrame(
        rows,
        "query string, product_title string, product_brand string, product_color string, esci_label string",
    )


def test_pair_overlap_has_explicit_denominators(spark):
    frame = _frame(spark, [("red red mug", "red ceramic mug", None, "red", "E")])
    row = build_features(frame).first()
    assert row.query_token_count == 3  # Repeated search terms are retained here.
    assert row.title_token_count == 3
    assert row.token_intersection_count == 2
    assert row.query_coverage == 1  # Both distinct query terms occur in the title.
    assert row.title_coverage == pytest.approx(2 / 3)
    assert row.token_jaccard == pytest.approx(2 / 3)
    assert row.exact_title_match == 0
    assert row.query_in_title == 0
    assert row.color_match == 1
    assert row.brand_match == 0


def test_normalization_matches_full_tokens_and_brand(spark):
    frame = _frame(
        spark,
        [
            (" ACME, Blue Mug! ", "Acme blue mug", "ACME", "Blue", "E"),
            ("mug", "Smug smile decoration", "Acme", None, "I"),
            ("café", "Café cup", None, None, "S"),
        ],
    )
    rows = build_features(frame).collect()
    assert rows[0].exact_title_match == rows[0].query_in_title == 1
    assert rows[0].brand_token_overlap == rows[0].brand_match == 1
    assert rows[0].color_token_overlap == rows[0].color_match == 1
    assert rows[1].query_in_title == rows[1].token_intersection_count == 0
    assert rows[2].query_in_title == rows[2].query_coverage == 1


def test_numbers_are_lexical_signals_and_not_product_semantics(spark):
    frame = _frame(
        spark,
        [
            ("phone 14", "phone 13 case", None, None, "I"),
            ("phone 14", "14 inch phone display", None, None, "I"),
            ("phone", "phone 14 case", None, None, "C"),
        ],
    )
    rows = build_features(frame).collect()
    assert rows[0].query_has_number == rows[0].numeric_mismatch == 1
    assert rows[1].query_has_number == 1
    assert rows[1].numeric_mismatch == 0  # Same digits need not mean the same product.
    assert rows[2].query_has_number == rows[2].numeric_mismatch == 0


def test_missing_text_never_matches_and_features_are_finite(spark):
    frame = _frame(spark, [(None, None, None, None, "I"), ("!!!", "", " ", "", "I")])
    rows = build_features(frame).collect()
    for row in rows:
        assert row.title_missing == row.brand_missing == row.color_missing == 1
        assert row.query_coverage == row.token_jaccard == 0
        assert row.exact_title_match == row.query_in_title == 0
        assert all(math.isfinite(row[name]) for name in FEATURE_COLUMNS)


def test_labels_and_ids_cannot_change_features(spark):
    frame = _frame(spark, [("blue cup", "blue mug", "Acme", "blue", "E")]).withColumn(
        "example_id", F.lit("train-example")
    )
    changed = frame.withColumn("esci_label", F.lit("I")).withColumn("example_id", F.lit("test-example"))
    first = build_features(frame)
    second = build_features(changed)
    assert first.select(*FEATURE_COLUMNS).collect() == second.select(*FEATURE_COLUMNS).collect()
    assert first.columns[: len(frame.columns)] == frame.columns
    assert "PythonUDF" not in first._jdf.queryExecution().optimizedPlan().toString()


def test_rejects_missing_inputs_and_feature_name_collisions(spark):
    frame = _frame(spark, [("cup", "cup", None, None, "E")])
    with pytest.raises(ValueError, match="product_color"):
        build_features(frame.drop("product_color"))
    with pytest.raises(ValueError, match="query_coverage"):
        build_features(frame.withColumn("query_coverage", F.lit(0)))
