"""Synthetic checks of whole-query exclusion and held-out membership.

The pipeline rejects conflicting normalized texts within one query ID before
calling assign_splits. The first test deliberately includes such adversarial
rows to verify that exclusion by ID removes an entire group, not only the
individual rows whose text happened to match the test set.
"""

from pyspark.sql import functions as F

from search_quality.data import assign_splits


def _examples(spark, rows):
    return spark.createDataFrame(
        rows,
        "example_id string, query_id string, query string, product_id string, split string, esci_label string",
    )


def test_official_test_preserved_and_overlap_removes_entire_training_groups(spark):
    rows = [
        ("test-id", "shared-id", "test wording", "p1", "test", "E"),
        ("test-text", "test-only-id", "Café mug", "p2", "test", "S"),
        ("train-id-1", "shared-id", "different words", "p3", "train", "I"),
        ("train-id-2", "shared-id", "second wording", "p4", "train", "C"),
        ("train-text-1", "text-group", " CAFÉ\tMUG  ", "p5", "train", "E"),
        ("train-text-2", "text-group", "no shared text here", "p6", "train", "S"),
        ("train-safe", "safe-group", "green spoon", "p7", "train", "E"),
    ]
    examples = _examples(spark, rows)
    assigned, id_overlap, text_overlap, bad_ids = assign_splits(examples)
    actual = assigned.collect()
    assert {row.example_id for row in actual} == {"test-id", "test-text", "train-safe"}
    original_test = sorted(row for row in rows if row[4] == "test")
    preserved_test = sorted(
        tuple(row[column] for column in examples.columns)
        for row in actual
        if row.dataset_split == "test"
    )
    assert preserved_test == original_test
    assert {row.query_id for row in id_overlap.collect()} == {"shared-id"}
    assert {row.query_norm for row in text_overlap.collect()} == {"café mug"}
    assert {row.query_id for row in bad_ids.collect()} == {"shared-id", "text-group"}


def test_validation_groups_are_disjoint_and_assignment_is_order_independent(spark):
    rows = [
        (f"e-{i}-{j}", f"q-{i}", f"item {i}", f"p-{j}", "train", "E")
        for i in range(100)
        for j in range(2)
    ]
    # Equivalent text with another ID must stay in the same development split.
    rows += [
        ("normalized-duplicate", "duplicate-id", " ITEM\t0 ", "p0", "train", "S"),
        ("heldout", "heldout-id", "held out item", "p9", "test", "I"),
    ]
    first = assign_splits(_examples(spark, rows))[0].collect()
    second = assign_splits(_examples(spark, list(reversed(rows))).repartition(2))[0].collect()
    first_map = {row.example_id: row.dataset_split for row in first}
    second_map = {row.example_id: row.dataset_split for row in second}
    assert first_map == second_map
    assert set(first_map) == {row[0] for row in rows}
    assert set(first_map.values()) == {"train", "validation", "test"}
    assert first_map["heldout"] == "test"
    assert first_map["normalized-duplicate"] == first_map["e-0-0"]

    for grouping_field in ("query_id", "query_norm"):
        groups = {}
        for row in first:
            groups.setdefault(row[grouping_field], set()).add(row.dataset_split)
        assert all(len(splits) == 1 for splits in groups.values())


def test_split_assignment_does_not_depend_on_labels_or_products(spark):
    examples = _examples(
        spark,
        [("row", "query", "purple bowl", "p1", "train", "E")],
    )
    altered = examples.withColumn("esci_label", F.lit("I")).withColumn("product_id", F.lit("unseen"))
    original_split = assign_splits(examples)[0].select("dataset_split").first()
    altered_split = assign_splits(altered)[0].select("dataset_split").first()
    assert original_split == altered_split
