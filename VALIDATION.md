# Validation record

Updated for PROS 4.2.2 on macOS Apple silicon. This record describes release v1.1.0; v1.0.0 remains available for PROS 4.2.1.

The 4.2.2 update changes the binary base, compiler, release metadata, version markers and linker scripts. The control engine and wire protocol are unchanged. Native tests and diagnostic linking are rerun for this release; the companion app and simulator checks below were completed on the unchanged protocol implementation for v1.0.0.

## Passed

- C state engine and byte parser compiled with Clang, AddressSanitizer and UndefinedBehaviorSanitizer. Checks include opt-in, initialization readiness, physical-field priority, software mode mapping, session ownership, duplicate/out-of-order commands, malformed frames, integer overflow, heartbeat expiry, millisecond counter rollover, physical disconnect, release and ordinary-input preservation.
- The actual smart-motor movement functions compiled with a stub VEX layer: software STOP suppresses voltage, velocity, absolute/relative targets and profiled-velocity commands, while normal commands retain their behavior.
- Desktop unit tests: 4 passed. Includes 316 shared traces producing identical replies from the production C state engine and JavaScript simulator, chunked reply parsing, session/sequence matching, and acknowledgement timeout behavior.
- The official 4.2.2 linker scripts, version header, and package metadata were checked against the new kernel archive.
- Six modified/new firmware objects compiled for Cortex-A9 hard-float using ARM GNU 15.2.1 and ABI-patched local VEX SDK headers.
- The final installable archive was extracted into a clean diagnostic project. Both cold and hot firmware images linked successfully using the official PROS build rules. Expected existing LLEMU header deprecation warnings do not prevent the build; the diagnostic uses the native screen API and does not depend on LLEMU.
- Electron UI test launched the application and exercised claim, autonomous, driver, Space stop, field takeover, field disconnect, a short timed match, and lost-link STOP. The same workflow passed against the packaged app for v1.0.0; the app has not changed for this kernel update.
- Electron Web Serial permission handling and the V5 device chooser were exercised; selection was canceled without opening a hardware device.
- Production desktop bundle and Apple-silicon macOS .app package generated.
- Git diff whitespace checks passed.

## Scope of the firmware build

This is an archive overlay build, not a rebuild of every PROS/VEX SDK object. It replaces recf_control_core.c.o, recf_control_state.c.o, system_daemon.c.o, ser_daemon.c.o, controller.c.o and vdml_motors.c.o inside the official 4.2.2 libpros.a. The four replaced upstream source files match the 4.2.2 release apart from copyright comments. All other official archive members are retained. `dist/BUILD.json` records source and artifact hashes.

## Not physically verified

No V5 Controller/Brain USB-radio communication, physical field connection, or actual motor behavior was tested on hardware in this session. The Controller protocol implementation comes from pinned @v5x/serial 0.5.9. The first hardware acceptance test is the supplied motor-free diagnostic: connect only the Controller's USB, select modes, and verify the Brain screen. Then test the lease timeout and physical field priority before adding movement routines.

Windows/Linux app builds and timing under heavy robot load were not tested. Software STOP covers standard PROS smart-motor movement APIs and the mode task. User-created child tasks, direct VEX SDK calls, ADI PWM/servos and non-motor outputs need application-specific handling.
