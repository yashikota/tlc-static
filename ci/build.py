#!/usr/bin/env python3
"""Build, test and package TLC.

Linux targets run inside the Dockerfile's build stage; macOS and Windows run
on native GitHub Actions runners with GraalVM installed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REV = 'fad899c74ca87a38322c1a0fc4a7d72a7a0fba33'
# Commit time of REV (UTC). TLC derives its CalVer version from the build
# timestamp, so pinning it makes every platform report the same version.
REV_TIME = '2026-10-26T22:58:17'
VERSION = REV_TIME[:10].replace('-', '.') + '.' + REV_TIME[11:].replace(':', '')
TARGETS = ['linux-amd64', 'linux-arm64', 'macos-arm64', 'windows-amd64']
ANT = {
    'ant': '763acda4a69588c9ea8817a952851ff0c2fc4bffa1d081c2565dc407f29d5794',
    'ant-launcher': '5c8551990307a032336d98ddaed549a39a689f07d4d4c6b950601bf22b3d6a1b',
}


def run(command, *, cwd=ROOT, log=None):
    print('+', ' '.join(map(str, command)), flush=True)
    result = subprocess.run(list(map(str, command)), cwd=cwd, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, encoding='utf-8', errors='replace')
    print(result.stdout, end='', flush=True)
    if log:
        Path(log).write_text(result.stdout, encoding='utf-8')
    result.check_returncode()
    return result.stdout


def download(url, path, digest=None):
    if path.exists() and (not digest or hashlib.sha256(path.read_bytes()).hexdigest() == digest):
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    # urllib uses the runner's configured HTTPS proxy and certificate trust.
    with urllib.request.urlopen(url) as response, path.open('wb') as output:
        shutil.copyfileobj(response, output)
    if digest and hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise RuntimeError(f'Checksum mismatch: {path}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', required=True, choices=TARGETS)
    args = parser.parse_args()
    target = args.target
    linux = target.startswith('linux-')
    windows = target.startswith('windows-')
    for directory in ['dist', 'tools', 'native-config', 'release', 'ci-logs']:
        (ROOT/directory).mkdir(exist_ok=True)
    logs = ROOT/'ci-logs'

    def tool(name, *arguments, workdir=None, log=None):
        executable = shutil.which(name)
        if not executable:
            raise RuntimeError(f'Missing tool: {name}')
        return run([executable, *arguments], cwd=workdir or ROOT, log=log)

    work = ROOT.as_posix()

    # The Docker build supplies upstream/ from its source stage, without .git.
    if not (ROOT/'upstream').is_dir():
        run(['git', 'init', 'upstream'])
        run(['git', '-C', 'upstream', 'remote', 'add', 'origin', 'https://github.com/tlaplus/tlaplus.git'])
        run(['git', '-C', 'upstream', 'fetch', '--depth', '1', 'origin', REV])
        run(['git', '-C', 'upstream', 'checkout', '--detach', 'FETCH_HEAD'])
    if (ROOT/'upstream/.git').is_dir() and run(['git', '-C', 'upstream', 'rev-parse', 'HEAD']).strip() != REV:
        raise RuntimeError('Unexpected upstream revision')
    for artifact, digest in ANT.items():
        download(f'https://repo.maven.apache.org/maven2/org/apache/ant/{artifact}/1.10.15/{artifact}-1.10.15.jar',
                 ROOT/'tools'/f'{artifact}.jar', digest)

    source = 'upstream/tlatools/org.lamport.tlatools'
    tool('java', '-cp', f'{work}/tools/*', 'org.apache.tools.ant.Main', '-f', 'customBuild.xml',
         f'-Dgit.revision={REV}', f'-Dgit.shortRevision={REV[:7]}', '-Dgit.branch=master',
         f'-DISO8601={REV_TIME}.0Z', f'-DTODAY={REV_TIME[:10]}',
         'compile', 'compile-test', 'dist', workdir=f'{work}/{source}', log=logs/'ant.log')
    shutil.copy2(ROOT/source/'dist/tla2tools.jar', ROOT/'dist/tla2tools.jar')
    run([sys.executable, 'configure.py'])

    java = ['java', '-Xmx512m', '-cp', f'{work}/dist/tla2tools.jar', 'tlc2.TLC']
    run([sys.executable, 'verify.py', *java], log=logs/'jvm-verification.log')
    shutil.copytree(ROOT/'verification', logs/'jvm', dirs_exist_ok=True)

    options = ['--no-fallback', '-march=compatibility',
               '-J-Xmx4g', '--parallelism=2', f'-H:ConfigurationFileDirectories={work}/native-config',
               '-cp', f'{work}/dist/tla2tools.jar', '-o', f'{work}/dist/tlc', 'tlc2.TLC']
    if not windows:
        options.insert(0, '--enable-monitoring=jfr')
    if linux:
        options = ['--static', '--libc=musl', *options]
    tool('native-image', *options, log=logs/'native-build.log')
    run([sys.executable, 'verify.py'], log=logs/'native-verification.log')
    if f'Version {VERSION}' not in (ROOT/'verification/success.log').read_text(encoding='utf-8'):
        raise RuntimeError(f'Native TLC does not report version {VERSION}')
    shutil.copytree(ROOT/'verification', logs/'native', dirs_exist_ok=True)
    if json.loads((logs/'jvm/results.json').read_text()) != json.loads((logs/'native/results.json').read_text()):
        raise RuntimeError('JVM/native results differ')

    binary = ROOT/'dist'/('tlc.exe' if windows else 'tlc')
    if linux:
        headers = run(['readelf', '-l', binary])
        dynamic = run(['readelf', '-d', binary])
        if 'INTERP' in headers or '(NEEDED)' in dynamic:
            raise RuntimeError('Linux executable is not fully static')
        (logs/'linkage.log').write_text(headers+dynamic)
    elif windows:
        run(['dumpbin', '/headers', binary], log=logs/'headers.log')
        run(['dumpbin', '/dependents', binary], log=logs/'linkage.log')
    else:
        run(['file', binary], log=logs/'headers.log')
        run(['otool', '-L', binary], log=logs/'linkage.log')

    stage = ROOT/'dist'/f'tlc-{target}'
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir()
    # Archives hold only the executable and the licenses it must ship with.
    shutil.copy2(binary, stage/binary.name)
    for name in ['LICENSE', 'TLAplus-LICENSE.txt']:
        shutil.copy2(ROOT/name, stage/name)
    notices = [ROOT/'upstream/tlatools/org.lamport.tlatools'/relative for relative in [
        'lib/jline/jline-LICENSE.txt', 'lib/gson/gson-LICENSE',
        'src/org/apache/commons/math3/CommonsMath-LICENSE.txt',
        'src/org/apache/commons/math3/CommonsMath-NOTICE.txt']]
    legal = Path(os.environ['JAVA_HOME'])/'legal'
    notices += sorted(path for path in legal.rglob('*') if path.is_file())
    if linux:
        download('https://raw.githubusercontent.com/ifduyue/musl/v1.2.5/COPYRIGHT', ROOT/'tools/musl-COPYRIGHT')
        notices.append(ROOT/'tools/musl-COPYRIGHT')
    with (stage/'THIRD-PARTY-NOTICES.txt').open('w', encoding='utf-8', newline='\n') as output:
        for path in notices:
            name = path.relative_to(legal.parent) if path.is_relative_to(legal) else path.name
            output.write(f'{"=" * 72}\n{name}\n{"=" * 72}\n\n')
            output.write(path.read_text(encoding='utf-8', errors='replace').rstrip()+'\n\n')
    destination = ROOT/'release'/stage.name
    if windows:
        shutil.make_archive(str(destination), 'zip', root_dir=stage)
    else:
        with tarfile.open(str(destination)+'.tar.gz', 'w:gz') as archive:
            for path in sorted(stage.iterdir()):
                archive.add(path, arcname=path.name)


if __name__ == '__main__':
    main()
