import json, pathlib, re, zipfile
root=pathlib.Path(__file__).resolve().parent
classes=root/'upstream/tlatools/org.lamport.tlatools/class'
names=set()
for package in ['tlc2/module','tlc2/overrides','tlc2/tool/fp']:
    for p in (classes/package).glob('*.class'):
        names.add(p.relative_to(classes).as_posix()[:-6].replace('/','.'))
config=[dict(name=n,allDeclaredMethods=True,allDeclaredConstructors=True,allDeclaredFields=True) for n in sorted(names)]
(root/'native-config/reflect-config.json').write_text(json.dumps(config,indent=2)+'\n')
with zipfile.ZipFile(root/'dist/tla2tools.jar') as jar:
    resources = [n for n in jar.namelist() if not n.endswith('/') and (not n.endswith('.class') or n.startswith('tlc2/module/'))]
includes = [{'pattern': re.escape(n)} for n in resources]
(root/'native-config/resource-config.json').write_text(json.dumps({'resources':{'includes':includes}},indent=2)+'\n')
