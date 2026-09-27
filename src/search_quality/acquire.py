"""Download the immutable official ESCI release and record byte-level provenance."""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq

REVISION = '7916cdf6ab75a462e77f20ab40428a10923998d5'
FILES = ['shopping_queries_dataset_examples.parquet', 'shopping_queries_dataset_products.parquet']
# Verified from the Git LFS pointers at REVISION, not from a mutable local cache.
EXPECTED_SHA256 = {
    FILES[0]: '4a735b693b4a424a6fc67f5be6e4c811495c488bbf66d02a602d308b2744263a',
    FILES[1]: '25124442d064d64b26f74082d6fa09438d679efc0c183cf28d19064a2b65a265',
}


def acquire(root: Path):
    raw = root / 'data/raw'
    manifests = root / 'data/manifests'
    notices = root / 'references/upstream'
    for folder in [raw, manifests, notices]:
        folder.mkdir(parents=True, exist_ok=True)
    records = []
    for filename in FILES:
        url = f'https://media.githubusercontent.com/media/amazon-science/esci-data/{REVISION}/shopping_queries_dataset/{filename}'
        path = raw / filename
        if not path.exists():
            part = path.with_suffix('.parquet.part')
            subprocess.run(['curl', '-fL', '--retry', '3', '--silent', '--show-error', url, '-o', str(part)], check=True)
            with part.open('rb') as f:
                if f.read(4) != b'PAR1':
                    raise ValueError(f'{filename}: response is not Parquet (possibly LFS pointer/HTML).')
            pq.ParquetFile(part)  # Validate footer before publishing the download.
            part.replace(path)
        with path.open('rb') as f:
            if f.read(4) != b'PAR1':
                raise ValueError(f'Invalid Parquet header: {path}')
        meta = pq.ParquetFile(path)
        with path.open('rb') as f:
            sha = hashlib.file_digest(f, 'sha256').hexdigest()
        if sha != EXPECTED_SHA256[filename]:
            raise ValueError(f'{filename}: bytes do not match the pinned upstream Git LFS SHA-256')
        record = {'filename': filename, 'url': url, 'revision': REVISION,
                  'bytes': path.stat().st_size, 'sha256': sha, 'rows': meta.metadata.num_rows,
                  'schema': str(meta.schema_arrow), 'verified_utc': datetime.now(timezone.utc).isoformat(),
                  'license_url': f'https://github.com/amazon-science/esci-data/blob/{REVISION}/LICENSE'}
        records.append(record)
        print(f'Verified {filename}: {record["rows"]:,} rows / {record["bytes"]:,} bytes', flush=True)
    for name in ['LICENSE', 'NOTICE']:
        url = f'https://raw.githubusercontent.com/amazon-science/esci-data/{REVISION}/{name}'
        subprocess.run(['curl', '-fsSL', '--retry', '3', url, '-o', str(notices/f'ESCI-{name}')], check=True)
    manifest = {'dataset': 'Amazon ESCI', 'revision': REVISION, 'files': records}
    (manifests/'source.json').write_text(json.dumps(manifest, indent=2)+'\n')
    return manifest
