"""Conservative local Spark configuration and portable runtime discovery."""
import os
from pathlib import Path
import sys


def make_spark(root: Path, name: str = 'product-search-quality', threads: int = 4):
    if not os.environ.get('JAVA_HOME'):
        candidates = sorted((root/'.runtime/java').glob('**/bin/java'))
        if candidates:
            os.environ['JAVA_HOME'] = str(candidates[0].parent.parent)
    os.environ.setdefault('SPARK_LOCAL_IP', '127.0.0.1')
    os.environ['PYSPARK_PYTHON'] = sys.executable
    scratch = root/'.runtime/spark'
    events = root/'experiments/runs/spark-events'
    scratch.mkdir(parents=True, exist_ok=True)
    events.mkdir(parents=True, exist_ok=True)
    from pyspark.sql import SparkSession
    spark = (SparkSession.builder.master(f'local[{threads}]').appName(name)
             .config('spark.driver.memory', '4g')
             .config('spark.driver.host', '127.0.0.1')
             .config('spark.driver.bindAddress', '127.0.0.1')
             .config('spark.sql.shuffle.partitions', '16')
             .config('spark.sql.adaptive.enabled', 'true')
             .config('spark.sql.execution.arrow.pyspark.enabled', 'true')
             .config('spark.local.dir', str(scratch))
             .config('spark.eventLog.enabled', 'true')
             .config('spark.eventLog.dir', events.as_uri())
             .config('spark.ui.showConsoleProgress', 'false')
             .getOrCreate())
    spark.sparkContext.setLogLevel('ERROR')
    return spark
