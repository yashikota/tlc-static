#!/usr/bin/env python3
"""Pin a new TLA+ commit: ./ci/bump_upstream.py <sha>.

Rewrites every reference to the old commit and its CalVer version, then
prints the new version. Prints nothing if <sha> is already pinned.
"""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'ci'))
import build  # noqa: E402


def git(*args, cwd=ROOT):
    return subprocess.run(['git', *args], cwd=cwd, check=True, stdout=subprocess.PIPE, text=True).stdout


def main():
    rev = sys.argv[1]
    if not re.fullmatch(r'[0-9a-f]{40}', rev):
        raise SystemExit(f'Not a full commit SHA: {rev}')
    if rev == build.REV:
        return
    with tempfile.TemporaryDirectory() as tmp:
        git('init', '-q', tmp)
        git('fetch', '-q', '--depth', '1', 'https://github.com/tlaplus/tlaplus.git', rev, cwd=tmp)
        stamp = git('log', '-1', '--date=format-local:%Y-%m-%dT%H:%M:%S', '--format=%cd', 'FETCH_HEAD',
                    cwd=tmp).strip()
    # format-local uses TZ, which the caller sets to UTC.
    old_version = build.VERSION
    version = stamp[:10].replace('-', '.') + '.' + stamp[11:].replace(':', '')
    # Workflow files are left alone: GITHUB_TOKEN may not push changes to them.
    for name in git('grep', '-l', '-e', build.REV, '-e', old_version, '--', '.', ':!.github/workflows').split():
        path = ROOT/name
        text = path.read_text(encoding='utf-8')
        text = text.replace(build.REV, rev).replace(old_version, version)
        text = text.replace(f"REV_TIME = '{build.REV_TIME}'", f"REV_TIME = '{stamp}'")
        path.write_text(text, encoding='utf-8')
    print(version)


if __name__ == '__main__':
    main()
