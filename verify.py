#!/usr/bin/env python3
"""Run with ./verify.py [command ...]; defaults to the native executable."""
import pathlib, subprocess, sys, re, json
root = pathlib.Path(__file__).resolve().parent
command = sys.argv[1:] or [str(root/('dist/tlc.exe' if sys.platform == 'win32' else 'dist/tlc')), '-Xmx512m']
logs = root/'verification'
logs.mkdir(exist_ok=True)
common = ['-workers','2','-fp','0','-seed','1','-fpbits','1','-fpmem','0.1','-noGenerateSpecTE']
cases = [
 ('success', [], 0, ['No error has been found.', '5 states generated, 4 distinct states found']),
 ('invariant', ['-config','Violation.cfg'], 12, ['Invariant Bad is violated']),
 ('liveness', ['-config','Liveness.cfg'], 13, ['Temporal property Impossible was violated']),
 ('simulation', ['-simulate','num=10','-depth','20'], 0, ['Simulation using seed']),
 ('depth-first', ['-dfid','10','-workers','1','-config','Safety.cfg'], 0, ['No error has been found.']),
]
cases.append(('bakery', ['-config','Bakery.cfg'], 0, ['No error has been found.', '1183 states generated, 668 distinct states found']))
results=[]
for name, args, expected, messages in cases:
    p=subprocess.run(command+common+args+(['Bakery.tla'] if name=='bakery' else ['Counter.tla']), cwd=root/'tests', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', timeout=90)
    (logs/(name+'.log')).write_text(p.stdout)
    ok=p.returncode==expected and all(m in p.stdout for m in messages)
    results.append(dict(case=name,exit=p.returncode,expected=expected,passed=ok))
    print(name, 'PASS' if ok else 'FAIL', f'(exit {p.returncode})', flush=True)
    if not ok: print(p.stdout)
(logs/'results.json').write_text(json.dumps(results,indent=2)+'\n')
if not all(r['passed'] for r in results): sys.exit(1)
