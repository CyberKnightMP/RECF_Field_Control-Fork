#!/usr/bin/env python3
"""Test the state engine and actual motor movement functions with a stub VEX layer."""
from pathlib import Path
import subprocess,tempfile,os
root=Path(__file__).resolve().parents[2]
cc=os.environ.get('CC','clang')
flags=['-std=gnu11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-g']
with tempfile.TemporaryDirectory(prefix='recf-native-') as folder:
    folder=Path(folder)
    subprocess.run([cc,*flags,'-I'+str(root/'include'),str(root/'src/system/recf_control_core.c'),str(root/'tests/recf/test_core.c'),'-o',str(folder/'core')],check=True)
    subprocess.run([str(folder/'core')],check=True)
    # Compile the actual movement section from the production source, without
    # the platform's unrelated getters and RTOS headers. Only VEX IO is stubbed.
    source=(root/'src/devices/vdml_motors.c').read_text()
    section=source[source.index('#define MOTOR_MOVE_RANGE'):source.index('double motor_get_target_position')]
    (folder/'motors.c').write_text((root/'tests/recf/motor_stub.h').read_text()+section+(root/'tests/recf/motor_assertions.c').read_text())
    subprocess.run([cc,*flags,str(folder/'motors.c'),'-o',str(folder/'motors')],check=True)
    subprocess.run([str(folder/'motors')],check=True)
    print('Smart-motor commands: software STOP suppression and normal command regression tests passed')
