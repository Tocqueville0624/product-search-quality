-- Standalone Spark SQL audit queries. Execute each statement independently.
-- Expected temporary views, registered by the pipeline:
-- esci_examples: US large-version pairs before joining. Columns:
--   example_id, query_id, query, product_locale, product_id, esci_label, split.
-- esci_products: source product table, with product_locale, product_id,
--   product_title, product_brand, product_color (plus optional metadata).
-- esci_joined: row-preserving left join of the above on
--   (product_locale, product_id), with product_matched BOOLEAN created from a
--   non-null marker on the product side BEFORE joining. A null title alone
--   does not establish that the product join failed.
-- These queries describe a labeled benchmark, not production search traffic.

-- Q1: What is the label balance in each official split?
-- Denominator: all example pairs in that split, not users, clicks, or query volume.
SELECT split, esci_label, COUNT(*) AS pair_count,
       COUNT(DISTINCT query_id) AS query_count,
       COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY split) AS pair_share
FROM esci_examples
GROUP BY split, esci_label
ORDER BY split, esci_label;

-- Q2: Could the product join silently multiply pair rows?
-- Expected result is zero rows. Resolve duplicates before joining/modeling.
SELECT product_locale, product_id, COUNT(*) AS product_rows
FROM esci_products
WHERE product_locale = 'us'
GROUP BY product_locale, product_id
HAVING COUNT(*) > 1
ORDER BY product_rows DESC, product_locale, product_id;

-- Q3: Did the join preserve every input pair, and how many pairs did not match?
-- Input/output equality is necessary but not sufficient. Q2 must also pass.
SELECT (SELECT COUNT(*) FROM esci_examples) AS input_pair_count,
       COUNT(*) AS joined_pair_count,
       SUM(CASE WHEN product_matched THEN 0 ELSE 1 END) AS unmatched_pair_count,
       AVG(CASE WHEN product_matched THEN 1.0 ELSE 0.0 END) AS product_match_rate
FROM esci_joined;

-- Q4: How frequently is metadata unavailable to the relevance model?
-- Denominator: all joined pairs in the split. These flags include unmatched
-- products. Read alongside Q3 to distinguish absence from failed linkage.
SELECT split, COUNT(*) AS pair_count,
       SUM(CASE WHEN query IS NULL OR TRIM(query) = '' THEN 1 ELSE 0 END) AS missing_query,
       SUM(CASE WHEN product_title IS NULL OR TRIM(product_title) = '' THEN 1 ELSE 0 END) AS missing_title,
       SUM(CASE WHEN product_brand IS NULL OR TRIM(product_brand) = '' THEN 1 ELSE 0 END) AS missing_brand,
       SUM(CASE WHEN product_color IS NULL OR TRIM(product_color) = '' THEN 1 ELSE 0 END) AS missing_color
FROM esci_joined
GROUP BY split
ORDER BY split;

-- Q5: Are official query groups disjoint across the train/test split?
-- Expected result is zero rows. Normalized query-text and pair-overlap checks
-- are additional pipeline assertions. IDs alone cannot establish no leakage.
SELECT product_locale, query_id, COUNT(DISTINCT split) AS split_count
FROM esci_examples
GROUP BY product_locale, query_id
HAVING COUNT(DISTINCT split) > 1
ORDER BY product_locale, query_id;

-- Q6: How uneven are labeled candidate-set sizes across queries?
-- A large count means more benchmark candidates, not a popular search query.
WITH candidates AS (
    SELECT split, query_id, COUNT(*) AS candidate_count
    FROM esci_examples
    GROUP BY split, query_id
)
SELECT split, COUNT(*) AS query_count, MIN(candidate_count) AS minimum_candidates,
       PERCENTILE_APPROX(candidate_count, ARRAY(0.5, 0.9, 0.99)) AS candidate_quantiles,
       MAX(candidate_count) AS maximum_candidates
FROM candidates
GROUP BY split
ORDER BY split;
