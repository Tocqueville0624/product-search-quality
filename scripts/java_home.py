"""Print the available Java home without changing the global shell setup."""
import os
from pathlib import Path

root = Path(__file__).resolve().parents[1]
existing = os.environ.get('JAVA_HOME')
if existing and (Path(existing) / 'bin/java').is_file():
    print(existing)
else:
    matches = sorted((root / '.runtime/java').glob('**/bin/java'))
    if not matches:
        raise SystemExit('No local JDK; run scripts/bootstrap_java.py or set JAVA_HOME to Java 17.')
    print(matches[0].parent.parent)
