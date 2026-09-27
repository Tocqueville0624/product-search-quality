"""Local Spark classifiers, development selection, and one frozen test run."""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
import time
import tomllib
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from pyspark.ml import Pipeline, PipelineModel
from pyspark.ml.classification import LogisticRegression
from pyspark.ml.feature import StandardScaler, VectorAssembler
from pyspark.ml.functions import vector_to_array
from pyspark.sql import functions as F

from .data import SEED
from .evaluation import LABELS, classification_metrics, query_bootstrap, review_metrics
from .features import FEATURE_COLUMNS


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')


def code_hashes(root):
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted((root / 'src/search_quality').glob('*.py'))}


def artifact_hashes(root, directories):
    result = {}
    for directory in directories:
        for path in sorted((root / directory).rglob('*')):
            if path.is_file() and not path.name.startswith('.'):
                with path.open('rb') as handle:
                    result[str(path.relative_to(root))] = hashlib.file_digest(handle, 'sha256').hexdigest()
    return result


def _settings(root):
    with (root / 'configs/study.toml').open('rb') as handle:
        config = tomllib.load(handle)
    if config['study']['seed'] != SEED or tuple(config['study']['labels']) != LABELS:
        raise ValueError('Study seed/label order must match the documented implementation')
    return config


def _labeled(df):
    mapping = F.create_map(*[value for i, label in enumerate(LABELS)
                             for value in (F.lit(label), F.lit(float(i)))])
    return df.withColumn('target', mapping[F.col('label')])


def _predict(model, frame):
    names = F.array(*[F.lit(label) for label in LABELS])
    return (model.transform(frame)
            .withColumn('prediction_label', names[F.col('prediction').cast('int')])
            .withColumn('p_e', vector_to_array('probability')[0])
            .select('example_id', 'query_id', 'label',
                    F.col('prediction_label').alias('prediction'), 'p_e',
                    'query_token_count', 'query_has_number', 'numeric_mismatch',
                    'brand_missing', 'title_missing', 'product_seen_train')
            .toPandas())


def _scores(predictions, config):
    return {'classification': classification_metrics(predictions),
            'review': review_metrics(predictions,
                budgets=config['review']['budget_fractions'], seed=SEED,
                repeats=config['review']['random_repeats'])}


def train(root, spark):
    if any((root / path).exists() for path in ['reports/test_metrics.json',
            'experiments/test_exposure.json', 'experiments/runs/test_predictions.parquet']):
        raise RuntimeError('Test already inspected. Start a documented exploratory study or fresh holdout.')
    started = time.monotonic()
    config = _settings(root)
    base = root / 'data/processed/features'
    # Partition pruning: this command never reads the test partition.
    train_df = _labeled(spark.read.parquet(str(base / 'dataset_split=train'))).cache()
    valid_df = _labeled(spark.read.parquet(str(base / 'dataset_split=validation'))).cache()
    counts = {row['label']: row['count'] for row in train_df.groupBy('label').count().collect()}
    if set(counts) != set(LABELS):
        raise ValueError('All four classes must exist in training')
    n_train = sum(counts.values())
    majority = max(LABELS, key=lambda label: counts[label])
    baseline = valid_df.select('example_id', 'query_id', 'label').toPandas()
    baseline['prediction'] = majority
    baseline['p_e'] = counts['E'] / n_train
    comparisons = {'majority': _scores(baseline, config)}
    candidates = [('logistic_unweighted', False), ('logistic_class_weighted', True)]
    metadata = {}
    for name, balanced in candidates:
        tick = time.monotonic()
        weights = {label: n_train / (4 * counts[label]) if balanced else 1.0 for label in LABELS}
        mapping = F.create_map(*[item for label, weight in weights.items()
                                for item in (F.lit(label), F.lit(weight))])
        fit_frame = train_df.withColumn('fit_weight', mapping[F.col('label')])
        pipeline = Pipeline(stages=[
            VectorAssembler(inputCols=FEATURE_COLUMNS, outputCol='raw_features'),
            StandardScaler(inputCol='raw_features', outputCol='features', withMean=True, withStd=True),
            LogisticRegression(featuresCol='features', labelCol='target', weightCol='fit_weight',
                               family='multinomial', regParam=0.05, elasticNetParam=0.0,
                               maxIter=100, tol=1e-6),
        ])
        model = pipeline.fit(fit_frame)
        model.write().overwrite().save(str(root / 'models' / name))
        predictions = _predict(model, valid_df)
        predictions.to_parquet(root / 'experiments/runs' / f'{name}_validation.parquet', index=False)
        comparisons[name] = _scores(predictions, config)
        coefficients = model.stages[-1].coefficientMatrix.toArray()
        metadata[name] = {
            'class_weights': weights, 'iterations': model.stages[-1].summary.totalIterations,
            'seconds_fit_and_validation': round(time.monotonic() - tick, 3),
            'standardized_coefficients': {
                label: dict(zip(FEATURE_COLUMNS, coefficients[i].tolist())) for i, label in enumerate(LABELS)},
            'intercept': model.stages[-1].interceptVector.toArray().tolist(),
        }
        print(f"Validation {name}: macro-F1={comparisons[name]['classification']['macro_f1']:.4f}", flush=True)
    selected = max((name for name, _ in candidates), key=lambda name: comparisons[name]['classification']['macro_f1'])
    audit = json.loads((root / 'reports/data_audit.json').read_text())
    source = json.loads((root / 'data/manifests/source.json').read_text())
    revision = subprocess.run(['git', 'rev-parse', '--verify', 'HEAD'], cwd=root,
                              capture_output=True, text=True)
    freeze = {
        'status': 'frozen_before_test', 'frozen_at_utc': datetime.now(timezone.utc).isoformat(),
        'question': 'Classify relevance; prioritize non-Exact judgements inside the predicted-Exact pool.',
        'selected_model': selected, 'selection_rule': 'highest validation macro-F1 among two fixed candidates',
        'majority_label': majority, 'majority_p_e': counts['E'] / n_train,
        'label_order': list(LABELS), 'features': FEATURE_COLUMNS,
        'hyperparameters': {'regParam': 0.05, 'maxIter': 100, 'tol': 1e-6, 'family': 'multinomial'},
        'review_budgets': config['review']['budget_fractions'], 'random_repeats': config['review']['random_repeats'],
        'priority': 'ascending p_e, then example_id; same predicted-E pool; no labels in selection',
        'probability_caveat': 'Class-weighted scores are ranking signals, not calibrated natural-prevalence probabilities.',
        'slices': ['query length 1-2 vs 3+', 'query contains digits', 'numeric mismatch',
                   'brand missing', 'product seen in training'],
        'bootstrap': {'unit': 'query_id', 'replicates': 300, 'confidence': 0.95, 'budget': 0.10},
        'seed': SEED, 'training_rows': n_train, 'training_class_counts': counts,
        'data_source_manifest': source, 'splits': audit['splits'],
        'source_code_sha256': code_hashes(root),
        'frozen_artifact_directories': [f'models/{selected}', 'data/processed/features'],
        'artifact_sha256': artifact_hashes(root, [f'models/{selected}', 'data/processed/features']),
        'study_config_sha256': hashlib.sha256((root / 'configs/study.toml').read_bytes()).hexdigest(),
        'git_revision_at_run': revision.stdout.strip() if revision.returncode == 0 else 'uncommitted_initial_implementation',
        'environment': {'python': sys.version.split()[0], 'spark': spark.version, 'master': spark.sparkContext.master,
                        'platform': platform.system(), 'architecture': platform.machine(),
                        'driver_memory': spark.sparkContext.getConf().get('spark.driver.memory')},
        'elapsed_seconds': round(time.monotonic() - started, 3),
    }
    write_json(root / 'reports/validation_metrics.json', comparisons)
    write_json(root / 'reports/model_details.json', metadata)
    write_json(root / 'experiments/frozen_study.json', freeze)
    train_df.unpersist()
    valid_df.unpersist()
    return {'selected_model': selected, 'validation_macro_f1': comparisons[selected]['classification']['macro_f1'],
            'status': 'frozen_before_test', 'seconds': freeze['elapsed_seconds']}


def evaluate(root, spark):
    target = root / 'reports/test_metrics.json'
    if target.exists():
        raise RuntimeError('Final test already evaluated; preserve this result.')
    freeze = json.loads((root / 'experiments/frozen_study.json').read_text())
    if freeze['source_code_sha256'] != code_hashes(root):
        raise RuntimeError('Implementation changed since freeze; document and resolve before evaluating test')
    if freeze['study_config_sha256'] != hashlib.sha256((root / 'configs/study.toml').read_bytes()).hexdigest():
        raise RuntimeError('Study configuration changed since freeze')
    if freeze['artifact_sha256'] != artifact_hashes(root, freeze['frozen_artifact_directories']):
        raise RuntimeError('Data or selected fitted model changed since freeze')
    exposure = root / 'experiments/test_exposure.json'
    if exposure.exists():
        raise RuntimeError('Test evaluation previously started; document a technical recovery before retrying.')
    write_json(exposure, {'status': 'test_evaluation_started',
        'at_utc': datetime.now(timezone.utc).isoformat(), 'selected_model': freeze['selected_model'],
        'freeze_sha256': hashlib.sha256((root / 'experiments/frozen_study.json').read_bytes()).hexdigest()})
    config = _settings(root)
    test_df = spark.read.parquet(str(root / 'data/processed/features/dataset_split=test'))
    model = PipelineModel.load(str(root / 'models' / freeze['selected_model']))
    started = time.monotonic()
    predictions = _predict(model, test_df)
    predictions.to_parquet(root / 'experiments/runs/test_predictions.parquet', index=False)
    result = _scores(predictions, config)
    result['uncertainty'] = query_bootstrap(predictions, budget=0.10, n_bootstrap=300, seed=SEED)
    baseline = predictions.copy()
    baseline['prediction'] = freeze['majority_label']
    baseline['p_e'] = freeze['majority_p_e']
    result['majority_baseline'] = classification_metrics(baseline)
    slices = {
        'query_0_2_tokens': predictions.query_token_count <= 2,
        'query_3_plus_tokens': predictions.query_token_count >= 3,
        'query_contains_digits': predictions.query_has_number == 1,
        'query_no_digits': predictions.query_has_number == 0,
        'numeric_mismatch': predictions.numeric_mismatch == 1,
        'brand_missing': predictions.brand_missing == 1,
        'brand_present': predictions.brand_missing == 0,
        'product_seen_train': predictions.product_seen_train,
        'product_unseen_train': ~predictions.product_seen_train,
    }
    result['slices'] = {name: _scores(predictions.loc[mask], config) for name, mask in slices.items()}
    result.update({'status': 'verified_offline', 'selected_model': freeze['selected_model'],
                   'evaluated_at_utc': datetime.now(timezone.utc).isoformat(),
                   'seconds_inference_and_evaluation': round(time.monotonic() - started, 3),
                   'limitations': ['Published judgements, not live traffic or conversion.',
                                   'Model and review policy selected on development data only.',
                                   'No human labels were collected in this run.',
                                   'Within supplied candidate pairs, not full-catalogue retrieval.']})
    write_json(target, result)
    return {'status': result['status'], 'model': freeze['selected_model'],
            'macro_f1': result['classification']['macro_f1'], 'review': result['review']}
