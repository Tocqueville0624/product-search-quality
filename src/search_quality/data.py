"""Audit and split query groups before materializing any model inputs."""
import hashlib
import json
import time
from pathlib import Path

from pyspark.sql import functions as F

SEED = 20260926


def normalized_query(column='query'):
    return F.lower(F.trim(F.regexp_replace(F.coalesce(F.col(column), F.lit('')), r'\s+', ' ')))


def assign_splits(examples):
    """Keep the official test; remove entire train query IDs that overlap test text/IDs."""
    examples = examples.withColumn('query_norm', normalized_query())
    test = examples.filter(F.col('split') == 'test')
    train = examples.filter(F.col('split') == 'train')
    id_overlap = train.select('query_id').distinct().join(test.select('query_id').distinct(), 'query_id', 'inner')
    text_overlap = train.select('query_norm').distinct().join(test.select('query_norm').distinct(), 'query_norm', 'inner')
    bad_ids = (id_overlap.union(train.join(text_overlap, 'query_norm').select('query_id')).distinct())
    train = train.join(bad_ids, 'query_id', 'left_anti')
    # Normalized-query grouping prevents equivalent text going to train and validation.
    train = train.withColumn('dataset_split', F.when(F.pmod(F.xxhash64('query_norm', F.lit(SEED)), F.lit(10000)) < 2000, 'validation').otherwise('train'))
    test = test.withColumn('dataset_split', F.lit('test'))
    return train.unionByName(test), id_overlap, text_overlap, bad_ids


def query_hash(df):
    digest = hashlib.sha256()
    for row in df.select('query_id', 'query_norm').distinct().orderBy('query_id', 'query_norm').toLocalIterator():
        digest.update(json.dumps(list(row), ensure_ascii=False, separators=(',', ':')).encode()+b'\n')
    return digest.hexdigest()


def prepare(root: Path, spark):
    start = time.monotonic()
    out = root/'reports'
    out.mkdir(exist_ok=True)
    from .features import build_features, FEATURE_COLUMNS
    raw = root/'data/raw'
    examples_all = spark.read.parquet(str(raw/'shopping_queries_dataset_examples.parquet'))
    products_all = spark.read.parquet(str(raw/'shopping_queries_dataset_products.parquet'))
    examples = examples_all.filter((F.col('product_locale') == 'us') & (F.col('large_version') == 1))
    products = products_all.filter(F.col('product_locale') == 'us').select('product_locale', 'product_id', 'product_title', 'product_brand', 'product_color')
    keys = ['product_locale','product_id']
    n_examples = examples.count()
    n_products = products.count()
    duplicate_products = products.groupBy(*keys).count().filter('count > 1').count()
    duplicate_ids = examples.groupBy('example_id').count().filter('count > 1').count()
    if duplicate_products or duplicate_ids:
        raise ValueError(f'Duplicate product keys={duplicate_products}, example IDs={duplicate_ids}; manual policy required.')
    invalid = (F.col('query').isNull() | (normalized_query() == '') | F.col('query_id').isNull()
               | F.col('example_id').isNull() | F.col('product_id').isNull()
               | F.col('esci_label').isNull() | ~F.col('esci_label').isin('E','S','C','I')
               | F.col('split').isNull() | ~F.col('split').isin('train','test'))
    if examples.filter(invalid).count():
        raise ValueError('Missing query/ID, unexpected label, or invalid official split.')
    if products.filter(F.col('product_id').isNull()).count():
        raise ValueError('Missing product join key.')
    # Multiple raw spellings per ID could break a text-based validation split; stop if found.
    if examples.withColumn('query_norm', normalized_query()).groupBy('query_id').agg(F.countDistinct('query_norm').alias('n')).filter('n > 1').count():
        raise ValueError('A query ID has multiple normalized texts; revise grouping before proceeding.')
    # Exercise the complete transformation on a deterministic ~0.1% query sample first.
    sample = examples.filter(F.pmod(F.xxhash64('query_id', F.lit(SEED)), F.lit(1000)) == 0)
    sample_assigned, _, _, _ = assign_splits(sample)
    sample_features = build_features(sample_assigned.join(products, keys, 'left')).cache()
    sample_counts = [row.asDict() for row in sample_features.groupBy('dataset_split').count().collect()]
    if not sample_counts or sample_features.filter(F.col('query_coverage').isNull()).count():
        raise ValueError('Real-data sample transformation failed.')
    (out/'sample_smoke.json').write_text(json.dumps({'status':'verified', 'query_hash_modulus':1000,
        'rows_by_split':sample_counts, 'feature_count':len(FEATURE_COLUMNS)},indent=2)+'\n')
    sample_features.unpersist()
    assigned, id_overlap, text_overlap, bad_ids = assign_splits(examples)
    overlaps = {'query_ids': id_overlap.count(), 'normalized_query_texts': text_overlap.count(), 'excluded_train_query_ids': bad_ids.count()}
    joined_all = examples.join(products.withColumn('product_matched',F.lit(True)),keys,'left').fillna({'product_matched':False})
    join_count = joined_all.count()
    if join_count != n_examples:
        raise ValueError('Join changed the number of pairs.')
    unmatched = joined_all.filter(~F.col('product_matched')).count()
    # Retain missing-title rows; missingness is an explicit model feature.
    joined = assigned.join(products.withColumn('product_matched',F.lit(True)),keys,'left').fillna({'product_matched':False})
    train_products = assigned.filter("dataset_split = 'train'").select(*keys).distinct().withColumn('product_seen_train',F.lit(True))
    joined = joined.join(train_products,keys,'left').fillna({'product_seen_train':False})
    featured = build_features(joined).withColumnRenamed('esci_label','label')
    selected = ['example_id','query_id','query_norm','query','product_id','product_title','product_brand','label','dataset_split','product_seen_train']+FEATURE_COLUMNS
    destination = root/'data/processed/features'
    featured.select(*selected).write.mode('overwrite').partitionBy('dataset_split').parquet(str(destination))
    saved = spark.read.parquet(str(destination))
    split_records = [r.asDict() for r in saved.groupBy('dataset_split','label').count().orderBy('dataset_split','label').collect()]
    split_info = {}
    for split in ['train','validation','test']:
        subset = saved.filter(F.col('dataset_split') == split)
        split_info[split] = {'rows':subset.count(), 'queries':subset.select('query_id').distinct().count(), 'query_sha256':query_hash(subset)}
    # Structural checks consume no model outputs or test performance.
    for a,b in [('train','validation'),('train','test'),('validation','test')]:
        aa=saved.filter(F.col('dataset_split')==a)
        bb=saved.filter(F.col('dataset_split')==b)
        assert aa.select('query_norm').distinct().join(bb.select('query_norm').distinct(),'query_norm').limit(1).count()==0
        assert aa.select('query_id').distinct().join(bb.select('query_id').distinct(),'query_id').limit(1).count()==0
    train_original=examples.filter("split='train'")
    test_original=examples.filter("split='test'")
    pair_overlap=train_original.select('query_id','product_id').distinct().join(test_original.select('query_id','product_id').distinct(),['query_id','product_id']).count()
    audit = {'status':'verified', 'seed':SEED, 'spark_version':spark.version, 'spark_master':spark.sparkContext.master,
             'raw_all_locale_pairs':examples_all.count(), 'raw_all_locale_products':products_all.count(),
             'us_large_pairs':n_examples,'us_products':n_products,'duplicate_product_keys':duplicate_products,'duplicate_example_ids':duplicate_ids,
             'joined_rows':join_count,'unmatched_products':unmatched,'missing_or_blank_titles':joined_all.filter(F.length(F.trim(F.coalesce(F.col('product_title'),F.lit(''))))==0).count(),
             'train_test_overlap':{**overlaps,'exact_queryid_product_pairs':pair_overlap},
             'excluded_train_rows':n_examples-sum(x['rows'] for x in split_info.values()),
             'policy':'Preserve official test; remove whole training query IDs overlapping test query ID or lowercase/whitespace-normalized text; validation is xxhash64(normalized text, seed) modulo 10000 < 2000.',
             'splits':split_info,'label_counts':split_records,'feature_columns':FEATURE_COLUMNS,'elapsed_seconds':round(time.monotonic()-start,2)}
    (out/'data_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    examples.createOrReplaceTempView('esci_examples')
    products.createOrReplaceTempView('esci_products')
    joined_all.createOrReplaceTempView('esci_joined')
    sql_results=[]
    sql_text = '\n'.join(line for line in (root/'sql/data_quality.sql').read_text().splitlines()
                         if not line.lstrip().startswith('--'))
    for statement in sql_text.split(';'):
        if any(line.strip() and not line.strip().startswith('--') for line in statement.splitlines()):
            sql_results.append({'query':statement.strip(),'rows':[r.asDict() for r in spark.sql(statement).collect()]})
    (out/'sql_audit.json').write_text(json.dumps(sql_results,indent=2,default=str)+'\n')
    return audit
