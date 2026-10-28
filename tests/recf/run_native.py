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
    subprocess.run([cc,*flags,'-I'+str(root/'include'),str(root/'src/system/recf_control_core.c'),str(root/'tests/recf/test_watchdog.c'),'-o',str(folder/'watchdog')],check=True)
    subprocess.run([str(folder/'watchdog')],check=True)
    # Compile the actual movement section from the production source, without
    # the platform's unrelated getters and RTOS headers. Only VEX IO is stubbed.
    source=(root/'src/devices/vdml_motors.c').read_text()
    section=source[source.index('#define MOTOR_MOVE_RANGE'):source.index('double motor_get_target_position')]
    (folder/'motors.c').write_text((root/'tests/recf/motor_stub.h').read_text()+section+(root/'tests/recf/motor_assertions.c').read_text())
    subprocess.run([cc,*flags,str(folder/'motors.c'),'-o',str(folder/'motors')],check=True)
    subprocess.run([str(folder/'motors')],check=True)
    print('Smart-motor commands: software STOP suppression and normal command regression tests passed')

    adi=(root/'src/devices/vdml_ext_adi.c').read_text()
    pieces=[(root/'tests/recf/adi_stub.h').read_text(),adi[adi.index('static void recf_adi_config_set'):adi.index('#define ADI_MOTOR_MAX_SPEED')],adi[adi.index('static int32_t recf_adi_led_set'):adi.index('#define transform_adi_port')],adi[adi.index('#define transform_adi_port'):adi.index('/*\n * Validates 3 things:')]]
    for name in ['ext_adi_port_set_config','ext_adi_port_set_value','ext_adi_digital_write','ext_adi_motor_set']:
        begin=adi.index('int32_t '+name+'(');end=adi.index('\n}',begin)+2
        pieces.append(adi[begin:end])
    integration=(root/'src/system/recf_control_state.c').read_text()
    pieces.append('#undef vexDeviceAdiValueSet\n#undef vexDeviceAdiPortConfigSet\n')
    pieces.append(integration[integration.index('void recf_control_stop_motors(void)'):])
    pieces.append((root/'tests/recf/adi_assertions.c').read_text())
    (folder/'adi.c').write_text('\n'.join(pieces))
    subprocess.run([cc,*flags,'-I'+str(root/'include'),str(folder/'adi.c'),'-o',str(folder/'adi')],check=True)
    subprocess.run([str(folder/'adi')],check=True)
