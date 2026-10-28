#!/usr/bin/env python3
"""Build RECF_Control_State against a local VEX SDK and official PROS 4.2.2 archive."""
import argparse, collections, hashlib, json, os, shutil, subprocess, tempfile, zipfile
from pathlib import Path

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk', required=True, type=Path, help='VEX vexv5 directory (containing include/v5_api.h)')
    parser.add_argument('--toolchain', required=True, type=Path, help='ARM GNU bin directory')
    parser.add_argument('--base', required=True, type=Path, help='Official kernel@4.2.2.zip')
    parser.add_argument('--output', type=Path, default=root/'dist/kernel@4.2.2-recf.3.zip')
    args = parser.parse_args()
    suffix = '.exe' if os.name == 'nt' else ''
    gcc = args.toolchain/('arm-none-eabi-gcc'+suffix)
    ar = args.toolchain/('arm-none-eabi-ar'+suffix)
    if not (args.sdk/'include/v5_api.h').is_file(): parser.error('SDK is missing include/v5_api.h')
    if not gcc.is_file() or not ar.is_file(): parser.error('Toolchain must contain arm-none-eabi-gcc and arm-none-eabi-ar')
    files = ['system/recf_control_core.c','system/recf_control_state.c','system/system_daemon.c',
             'system/dev/ser_daemon.c','devices/controller.c','devices/vdml_motors.c','devices/vdml_ext_adi.c']
    with tempfile.TemporaryDirectory(prefix='recf-build-') as temporary:
        work = Path(temporary).resolve(); patched=work/'sdk'; patched.mkdir()
        # The VEX SDK wrappers use AAPCS. Apply the same ABI annotation as PROS patch_headers.py.
        for header in (args.sdk/'include').glob('*.h'):
            lines=[]; skip=False
            for line in header.read_text().splitlines():
                if skip:
                    if not line.endswith('\\'): skip=False
                    continue
                text=line.strip()
                if text.startswith(('/', '*', '#', '}', '{', 'extern', 'typedef', 'struct', 'enum')) or not text or ');' not in line:
                    lines.append(line)
                    if text.startswith('#') and line.endswith('\\'): skip=True
                else: lines.append('__attribute__((pcs("aapcs"))) '+line)
            (patched/header.name).write_text('\n'.join(lines)+'\n')
        flags=['-mcpu=cortex-a9','-mthumb','-mfpu=neon-fp16','-mfloat-abi=hard','-std=gnu23','-Os','-g',
               '-ffunction-sections','-fdata-sections','-funwind-tables','-Wall','-Wextra',
               '-Wno-unused-parameter','-Wno-enum-conversion','-D_POSIX_THREADS',
               '-D_UNIX98_THREAD_MUTEX_ATTRIBUTES','-D_POSIX_TIMERS','-D_POSIX_MONOTONIC_CLOCK',
               '-I',str(root/'include'),'-I',str(patched)]
        objects=[]
        for source in files:
            obj=work/(Path(source).name+'.o'); objects.append(obj)
            subprocess.run([str(gcc),*flags,'-c',str(root/'src'/source),'-o',str(obj)],check=True)
            print('Compiled',source,flush=True)
        package=work/'package';package.mkdir()
        with zipfile.ZipFile(args.base) as archive:
            # The base is a local caller-selected template; still reject traversal entries.
            for name in archive.namelist():
                destination=(package/name).resolve()
                if not destination.is_relative_to(package): raise ValueError('Unsafe archive path')
            archive.extractall(package)
        meta=json.loads((package/'template.pros').read_text());state=meta['py/state']
        if state.get('name')!='kernel' or state.get('version')!='4.2.2': raise ValueError('Expected the official PROS 4.2.2 kernel template')
        members=subprocess.check_output([str(ar),'t',str(package/'firmware/libpros.a')],text=True).splitlines()
        for name in ['system_daemon.c.o','ser_daemon.c.o','controller.c.o','vdml_motors.c.o','vdml_ext_adi.c.o']:
            if members.count(name)!=1: raise ValueError('Unexpected base archive member: '+name)
        for name in ['api.h','pros/recf_control_state.h']:
            shutil.copyfile(root/'include'/name,package/'include'/name)
        shutil.copyfile(root/'examples/recf_control/main.cpp',package/'src/main.cpp')
        subprocess.run([str(ar),'rcs',str(package/'firmware/libpros.a'),*map(str,objects)],check=True)
        counts=collections.Counter(subprocess.check_output([str(ar),'t',str(package/'firmware/libpros.a')],text=True).splitlines())
        assert all(counts[obj.name]==1 for obj in objects), 'Duplicate or missing object members'
        state['version']='4.2.2-recf.3';state['system_files'].append('include/pros/recf_control_state.h')
        state['metadata']['recf_control_state']='1.3.0'
        (package/'template.pros').write_text(json.dumps(meta,indent=2)+'\n')
        args.output.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(args.output,'w',zipfile.ZIP_DEFLATED) as archive:
            for file in sorted(package.rglob('*')):
                if file.is_file(): archive.write(file,file.relative_to(package))
        manifest={'product':'RECF_Control_State','version':'1.3.0','base_kernel':'4.2.2',
                  'base_sha256':sha(args.base),'output_sha256':sha(args.output),
                  'compiler':subprocess.check_output([str(gcc),'--version'],text=True).splitlines()[0],
                  'objects':[o.name for o in objects],
                  'sources':{name:sha(root/'src'/name) for name in files},
                  'method':'Replace seven archive members; retain other official kernel/SDK objects unchanged.',
                  'hardware_tested':False}
        (args.output.parent/'BUILD.json').write_text(json.dumps(manifest,indent=2)+'\n')
        print('Built',args.output)
if __name__=='__main__': main()
