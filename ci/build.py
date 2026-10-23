#!/usr/bin/env python3
"""Build, test and package TLC on native GitHub Actions runners."""
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
REV = '606dfa48298a1b36c4ee4625c705041c35bd7393'
IMAGES = {
    'linux-amd64': 'ghcr.io/graalvm/native-image-community@sha256:bd08fee5f6effb210e829f434e5b5341d9b5b321ddc47363a241853723c810eb',
    'linux-arm64': 'bellsoft/liberica-native-image-kit-container@sha256:b531f62a40ca4217df6f39b2f7c171f4503406f3ea1273ef450e6f96b8a6afa2',
}
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
    path.parent.mkdir(parents=True, exist_ok=True)
    # urllib uses the runner's configured HTTPS proxy and certificate trust.
    with urllib.request.urlopen(url) as response, path.open('wb') as output:
        shutil.copyfileobj(response, output)
    if digest and hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise RuntimeError(f'Checksum mismatch: {path}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', required=True, choices=[*IMAGES, 'macos-amd64', 'macos-arm64', 'windows-amd64'])
    args = parser.parse_args()
    target = args.target
    linux = target.startswith('linux-')
    windows = target.startswith('windows-')
    for directory in ['dist', 'tools', 'native-config', 'release', 'ci-logs']:
        (ROOT/directory).mkdir(exist_ok=True)
    logs = ROOT/'ci-logs'
    if linux:
        image = IMAGES[target]
        run(['docker', 'pull', image])
        docker = ['docker', 'run', '--rm', '--user', f'{os.getuid()}:{os.getgid()}',
                  '-v', f'{ROOT}:/work', '-w', '/work']

        def tool(name, *arguments, workdir=None, log=None):
            return run(docker + (['-w', workdir] if workdir else []) +
                       ['--entrypoint', name, image, *arguments], log=log)

        work = '/work'
    else:
        def tool(name, *arguments, workdir=None, log=None):
            executable = shutil.which(name)
            if not executable:
                raise RuntimeError(f'Missing tool: {name}')
            return run([executable, *arguments], cwd=workdir or ROOT, log=log)

        work = ROOT.as_posix()

    if not (ROOT/'upstream/.git').is_dir():
        run(['git', 'init', 'upstream'])
        run(['git', '-C', 'upstream', 'remote', 'add', 'origin', 'https://github.com/tlaplus/tlaplus.git'])
        run(['git', '-C', 'upstream', 'fetch', '--depth', '1', 'origin', REV])
        run(['git', '-C', 'upstream', 'checkout', '--detach', 'FETCH_HEAD'])
    if run(['git', '-C', 'upstream', 'rev-parse', 'HEAD']).strip() != REV:
        raise RuntimeError('Unexpected upstream revision')
    for artifact, digest in ANT.items():
        download(f'https://repo.maven.apache.org/maven2/org/apache/ant/{artifact}/1.10.15/{artifact}-1.10.15.jar',
                 ROOT/'tools'/f'{artifact}.jar', digest)

    source = 'upstream/tlatools/org.lamport.tlatools'
    tool('java', '-cp', f'{work}/tools/*', 'org.apache.tools.ant.Main', '-f', 'customBuild.xml',
         f'-Dgit.revision={REV}', f'-Dgit.shortRevision={REV[:7]}', '-Dgit.branch=master',
         'compile', 'compile-test', 'dist', workdir=f'{work}/{source}', log=logs/'ant.log')
    shutil.copy2(ROOT/source/'dist/tla2tools.jar', ROOT/'dist/tla2tools.jar')
    run([sys.executable, 'configure.py'])

    java = ['java', '-Xmx512m', '-cp', f'{work}/dist/tla2tools.jar', 'tlc2.TLC']
    if linux:
        java = docker + ['-w', '/work/tests', '--entrypoint', 'java', image, *java[1:]]
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
        # Prove it runs with neither a JVM nor a dynamic loader present.
        run(['docker', 'build', '-f', 'Dockerfile.scratch', '-t', 'tlc-scratch', '.'])
        run(['docker', 'run', '--rm', '--tmpfs', '/tmp:rw,mode=1777', '-v',
             f'{ROOT}/tests:/models', 'tlc-scratch', '-Xmx512m', '-workers', '2',
             '-fpmem', '0.1', '-noGenerateSpecTE', 'Counter.tla'], log=logs/'scratch.log')
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
    shutil.copy2(binary, stage/binary.name)
    for name in ['README.md', 'README.ja.md', 'VERIFICATION.md', 'LICENSE', 'TLAplus-LICENSE.txt']:
        shutil.copy2(ROOT/name, stage/name)
    for name in ['examples', 'licenses', 'verification']:
        (stage/name).mkdir()
    for pattern in ['*.tla', '*.cfg']:
        for path in (ROOT/'tests').glob(pattern):
            shutil.copy2(path, stage/'examples'/path.name)
    shutil.copytree(logs, stage/'verification', dirs_exist_ok=True)
    for relative in ['LICENSE', 'tlatools/org.lamport.tlatools/lib/jline/jline-LICENSE.txt',
                     'tlatools/org.lamport.tlatools/lib/gson/gson-LICENSE',
                     'tlatools/org.lamport.tlatools/src/org/apache/commons/math3/CommonsMath-LICENSE.txt',
                     'tlatools/org.lamport.tlatools/src/org/apache/commons/math3/CommonsMath-NOTICE.txt']:
        path = ROOT/'upstream'/relative
        shutil.copy2(path, stage/'licenses'/path.name)
    if linux:
        tool('/bin/sh', '-ec', f'cp -rL "$JAVA_HOME/legal" /work/dist/{stage.name}/licenses/java')
        download('https://raw.githubusercontent.com/ifduyue/musl/v1.2.5/COPYRIGHT', stage/'licenses/musl-COPYRIGHT')
    else:
        shutil.copytree(Path(os.environ['JAVA_HOME'])/'legal', stage/'licenses/java', symlinks=False)
    metadata = dict(target=target, upstream=REV, fully_static=linux,
                    toolchain=IMAGES[target] if linux else 'GraalVM CE 24.0.2',
                    source_commit=os.environ.get('GITHUB_SHA', 'local'))
    (stage/'BUILD.json').write_text(json.dumps(metadata, indent=2)+'\n')
    checksum = hashlib.sha256(binary.read_bytes()).hexdigest()
    (stage/'SHA256SUMS').write_text(f'{checksum}  {binary.name}\n')
    destination = ROOT/'release'/stage.name
    if windows:
        shutil.make_archive(str(destination), 'zip', root_dir=stage)
    else:
        with tarfile.open(str(destination)+'.tar.gz', 'w:gz') as archive:
            for path in sorted(stage.iterdir()):
                archive.add(path, arcname=path.name)


if __name__ == '__main__':
    main()
