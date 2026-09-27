"""Publish small execution counters, excluding full logs and local machine properties."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
summaries = []
for path in sorted((root / 'experiments/runs/spark-events').glob('*')):
    if not path.is_file() or path.name.startswith('.'):
        continue
    run = {'jobs': 0, 'completed_stages': 0, 'completed_tasks': 0,
           'shuffle_read_bytes': 0, 'shuffle_write_bytes': 0, 'executor_run_time_ms_sum': 0}
    executors = set()
    with path.open() as handle:
        for line in handle:
            event = json.loads(line)
            kind = event['Event']
            if kind == 'SparkListenerApplicationStart':
                run.update(application_id=event['App ID'], application_name=event['App Name'], start_ms=event['Timestamp'])
            elif kind == 'SparkListenerApplicationEnd':
                run['end_ms'] = event['Timestamp']
            elif kind == 'SparkListenerJobStart':
                run['jobs'] += 1
            elif kind == 'SparkListenerStageCompleted':
                run['completed_stages'] += 1
            elif kind == 'SparkListenerTaskEnd':
                run['completed_tasks'] += 1
                executors.add(event['Task Info']['Executor ID'])
                metrics = event.get('Task Metrics', {})
                read = metrics.get('Shuffle Read Metrics', {})
                run['shuffle_read_bytes'] += read.get('Remote Bytes Read', 0) + read.get('Local Bytes Read', 0)
                run['shuffle_write_bytes'] += metrics.get('Shuffle Write Metrics', {}).get('Shuffle Bytes Written', 0)
                run['executor_run_time_ms_sum'] += metrics.get('Executor Run Time', 0)
            elif kind == 'SparkListenerEnvironmentUpdate':
                props = event.get('Spark Properties', {})
                run['master'] = props.get('spark.master')
                run['driver_memory'] = props.get('spark.driver.memory')
    if 'end_ms' not in run:
        raise ValueError('Refusing to summarize an incomplete Spark application')
    run['application_wall_seconds'] = (run.pop('end_ms') - run['start_ms']) / 1000
    run['executor_ids'] = sorted(executors)
    summaries.append(run)
summaries.sort(key=lambda value: value['start_ms'])
report = {'status': 'verified_event_log_counters',
    'scope': 'Original reference run only; local execution, no worker cluster or cloud service.',
    'interpretation': 'Task runtime is summed across tasks; it is not application wall time. Shuffle includes local shuffle.',
    'applications': summaries}
(root / 'reports/spark_execution.json').write_text(json.dumps(report, indent=2) + '\n')
print(f'Summarized {len(summaries)} completed Spark applications')
