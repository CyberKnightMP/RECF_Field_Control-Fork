#!/usr/bin/env python3
"""Build the combined Controller + heartbeat desktop app on its target OS."""
import ast,json,platform,subprocess,sys,zipfile,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[1]
source=root/'tools/python-practice-watchdog/controller_serial_test.py'
version=next(n.value.value for n in ast.parse(source.read_text()).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='APP_VERSION' for t in n.targets))
dist=root/'dist/apps';dist.mkdir(parents=True,exist_ok=True)
name='RECF Field Control'
windows=sys.platform=='win32'
args=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--windowed',
      '--onefile' if windows else '--onedir','--name',name,'--collect-submodules','serial',
      '--distpath',str(dist),'--workpath',str(root/'dist/app-build'),'--specpath',str(root/'dist'),str(source)]
if not windows:args += ['--osx-bundle-identifier','org.offbrandwindow.recf-field-control']
subprocess.run(args,check=True)
app=dist/(name+'.exe' if windows else name+'.app')
exe=app if windows else app/'Contents/MacOS'/name
report=dist/'smoke-test.json'
proc=subprocess.Popen([str(exe),'--self-test-output',str(report)])
try: assert proc.wait(timeout=60)==0
except BaseException: proc.kill();raise
result=json.loads(report.read_text());assert result['app_version']==version
assert result['auton_packet']=='c936b84758c1050a0f0000004692'
label='windows-x64' if windows else 'macos-'+('arm64' if platform.machine()=='arm64' else 'x64')
archive=dist/f'RECF-Field-Control-{version}-{label}.zip'
if windows:
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:z.write(app,app.name)
else:subprocess.run(['ditto','-c','-k','--sequesterRsrc','--keepParent',str(app),str(archive)],check=True)
manifest={'version':version,'platform':label,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
          'frozen_smoke_test':result,'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
          'hardware_tested':False,'signed':False}
(archive.with_suffix('.json')).write_text(json.dumps(manifest,indent=2)+'\n')
print(archive)
