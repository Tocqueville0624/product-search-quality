# Spark SQL audits

`data_quality.sql` contains six queries executed by `search_quality.data.prepare` against US data views: label mix, duplicate product keys, join coverage, missing metadata, official query overlap, and candidate-pool sizes per query.

Verified results are in `reports/sql_audit.json`. Counts are benchmark rows/queries, never traffic, customers, or query popularity.
