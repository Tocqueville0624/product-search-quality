"""Reproduce the frozen design in a new ignored directory, preserving published results."""
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', default='local-run', help='New run directory name; existing runs are never overwritten')
    args = parser.parse_args()
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,60}', args.name):
        parser.error('Use a short name containing letters, digits, hyphens, or underscores')
    root = Path(__file__).resolve().parents[1]
    destination = root / '.reproduction' / args.name
    destination.mkdir(parents=True, exist_ok=False)
    for folder in ['src', 'configs', 'sql']:
        shutil.copytree(root / folder, destination / folder, ignore=shutil.ignore_patterns('__pycache__'))
    (root / 'data/raw').mkdir(parents=True, exist_ok=True)
    (destination / 'data').mkdir()
    (destination / 'data/raw').symlink_to(root / 'data/raw', target_is_directory=True)
    (destination / '.runtime').mkdir()
    if (root / '.runtime/java').exists():
        (destination / '.runtime/java').symlink_to(root / '.runtime/java', target_is_directory=True)
    environment = dict(os.environ, PYTHONPATH=str(destination / 'src'))
    for step in ['download', 'prepare', 'train', 'evaluate']:
        print(f'\nRunning {step} in .reproduction/{args.name}', flush=True)
        subprocess.run([sys.executable, '-m', 'search_quality', step, '--root', str(destination)],
                       cwd=root, env=environment, check=True)
    print(f'Reproduction complete: .reproduction/{args.name}/reports/test_metrics.json')


if __name__ == '__main__':
    main()
