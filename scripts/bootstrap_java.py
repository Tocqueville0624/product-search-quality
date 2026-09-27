"""Install a checksum-verified Temurin 17 JDK inside this project only."""
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    target = ROOT / '.runtime' / 'java'
    if list(target.glob('**/bin/java')):
        print('Existing project Java:', list(target.glob('**/bin/java'))[0])
        return
    os_name = {'Darwin': 'mac', 'Linux': 'linux'}.get(platform.system())
    arch = {'arm64': 'aarch64', 'aarch64': 'aarch64', 'x86_64': 'x64'}.get(platform.machine())
    if not os_name or not arch:
        raise SystemExit('Set JAVA_HOME to a supported Java 17 installation on this platform.')
    target.mkdir(parents=True, exist_ok=True)
    url = f'https://api.adoptium.net/v3/assets/latest/17/hotspot?architecture={arch}&image_type=jdk&os={os_name}&vendor=eclipse'
    info = json.loads(subprocess.check_output(['curl', '-fsSL', '--retry', '3', url]))[0]
    package = info['binary']['package']
    archive = target / package['name']
    subprocess.run(['curl', '-fL', '--retry', '3', '--silent', '--show-error', package['link'], '-o', str(archive)], check=True)
    digest = hashlib.file_digest(archive.open('rb'), 'sha256').hexdigest()
    if digest != package['checksum']:
        raise SystemExit('JDK checksum mismatch; extraction aborted.')
    with tarfile.open(archive) as handle:
        handle.extractall(target, filter='data')
    (target / 'source.json').write_text(json.dumps({'release': info['release_name'], 'url': package['link'], 'sha256': digest}, indent=2)+'\n')
    archive.unlink()
    print('Installed project Java:', list(target.glob('**/bin/java'))[0])


if __name__ == '__main__':
    main()
