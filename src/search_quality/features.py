"""Deterministic lexical pair features implemented with Spark expressions.

These features inspect only the query and product metadata of the current pair.
They require no fitting, corpus statistics, labels, identifiers, or split flags.
Token normalization is deliberately simple; it cannot resolve synonyms, units,
negation, product compatibility, or whether a matching number means the same thing.
"""

from __future__ import annotations

from pyspark.sql import Column, DataFrame, functions as F


FEATURE_COLUMNS = [
    "query_token_count",
    "title_token_count",
    "token_intersection_count",
    "query_coverage",
    "title_coverage",
    "token_jaccard",
    "exact_title_match",
    "query_in_title",
    "brand_token_overlap",
    "brand_match",
    "color_token_overlap",
    "color_match",
    "query_has_number",
    "numeric_mismatch",
    "title_missing",
    "brand_missing",
    "color_missing",
]

_INPUT_COLUMNS = ("query", "product_title", "product_brand", "product_color")


def normalized_text(column: Column) -> Column:
    """Lowercase text; replace runs of non-letter/non-number characters by space."""
    return F.trim(
        F.regexp_replace(F.lower(F.coalesce(column, F.lit(""))), r"[^\p{L}\p{N}]+", " ")
    )


def _tokens(text: Column) -> Column:
    # The predicate is compiled into Spark's higher-order array expression, not
    # executed as a Python UDF. Empty strings produce an empty token array.
    return F.filter(F.split(text, " "), lambda token: token != F.lit(""))


def _ratio(numerator: Column, denominator: Column) -> Column:
    return F.when(denominator > 0, numerator / denominator).otherwise(F.lit(0.0))


def build_features(df: DataFrame) -> DataFrame:
    """Append 17 numeric lexical features while preserving all source columns.

    Required inputs are nullable string columns named ``query``,
    ``product_title``, ``product_brand``, and ``product_color``.

    Token counts include repetitions. Intersection/coverage/Jaccard operate on
    distinct token sets. ``brand_match``/``color_match`` require every metadata
    token to appear in the query; empty metadata never counts as a match.
    ``query_in_title`` matches a complete normalized token sequence.

    ``numeric_mismatch`` is 1 if a query contains a sequence of ASCII digits that
    is absent from the title. Decimal punctuation, units and digit semantics are
    not interpreted: e.g. ``7.5`` is represented by the chunks ``7`` and ``5``.
    This is an error-analysis signal rather than proof of incompatibility.

    All features are doubles for direct use by Spark's VectorAssembler.
    A name collision is rejected to avoid silently replacing source columns.
    """
    missing = sorted(set(_INPUT_COLUMNS) - set(df.columns))
    if missing:
        raise ValueError(f"Missing feature input columns: {', '.join(missing)}")
    collisions = sorted(set(FEATURE_COLUMNS) & set(df.columns))
    if collisions:
        raise ValueError(f"Feature columns already exist: {', '.join(collisions)}")

    query = normalized_text(F.col("query"))
    title = normalized_text(F.col("product_title"))
    brand = normalized_text(F.col("product_brand"))
    color = normalized_text(F.col("product_color"))
    query_tokens, title_tokens = _tokens(query), _tokens(title)
    query_set, title_set = F.array_distinct(query_tokens), F.array_distinct(title_tokens)
    brand_set, color_set = F.array_distinct(_tokens(brand)), F.array_distinct(_tokens(color))
    intersection = F.size(F.array_intersect(query_set, title_set))
    query_size, title_size = F.size(query_set), F.size(title_set)
    brand_overlap = F.size(F.array_intersect(query_set, brand_set))
    color_overlap = F.size(F.array_intersect(query_set, color_set))
    query_numbers = F.array_distinct(_tokens(F.trim(F.regexp_replace(query, r"[^0-9]+", " "))))
    title_numbers = F.array_distinct(_tokens(F.trim(F.regexp_replace(title, r"[^0-9]+", " "))))

    expressions = {
        "query_token_count": F.size(query_tokens),
        "title_token_count": F.size(title_tokens),
        "token_intersection_count": intersection,
        "query_coverage": _ratio(intersection, query_size),
        "title_coverage": _ratio(intersection, title_size),
        "token_jaccard": _ratio(intersection, F.size(F.array_union(query_set, title_set))),
        "exact_title_match": (F.length(query) > 0) & (query == title),
        "query_in_title": (F.length(query) > 0)
        & F.concat(F.lit(" "), title, F.lit(" ")).contains(
            F.concat(F.lit(" "), query, F.lit(" "))
        ),
        "brand_token_overlap": brand_overlap,
        "brand_match": (F.size(brand_set) > 0) & (brand_overlap == F.size(brand_set)),
        "color_token_overlap": color_overlap,
        "color_match": (F.size(color_set) > 0) & (color_overlap == F.size(color_set)),
        "query_has_number": F.size(query_numbers) > 0,
        "numeric_mismatch": F.size(F.array_except(query_numbers, title_numbers)) > 0,
        "title_missing": F.length(title) == 0,
        "brand_missing": F.length(brand) == 0,
        "color_missing": F.length(color) == 0,
    }
    return df.select(
        "*", *[expressions[name].cast("double").alias(name) for name in FEATURE_COLUMNS]
    )
