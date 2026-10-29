# Validation record

## v1.4.2+beta - edge cases or smth from an idiot + 4-instance tests
- Theoretical updates since I had a skill issue with accessing the VEX SDK
- Made kernel task access to the shared competition and watchdog state atomic, including the output-blocking decision. The serial parser remains owned by the serial-daemon task.
- Prevented invalid competition-mode values from indexing beyond the mode-name table.
- Added a four-instance isolation test and documented physical-field priority and the PROS-facing software-control behavior.
- Kept the programmer-facing template API-only: it ships the compiled kernel and public header, and the build now rejects packages containing RECF implementation files. The repository itself still contains the source.
- Refreshed the kernel compatibility fingerprint and the matching desktop checker.

Notes: 
- Native C state, watchdog, motor, and ADI tests passed, as did all 25 controller tests; identity and packaging-script syntax checks passed. Sanitizers were unavailable in Windows environment, and the ARM cross-compiler/VEX SDK needed for a firmware package build were not available, so hardware and cross-build validation remain outstanding.
- The published kernel/app artifacts are not rebuilt by these source changes. Rebuild matching artifacts before deploying; the source repository remains source-available, so making the repository itself closed-source would require a separate distribution/access change.

## v1.4.1 — desktop-only patch

- All 25 Python tests passed, including the empty macOS USB-registry case. An actual port-list invocation with no VEX USB device returned an empty list successfully.
- Kernel identity and the kernel@4.2.2-recf.4 binary remain unchanged from v1.4.0. PROS_RECF_TEST was updated from the public depot to that kernel and rebuilt cleanly with its original main.cpp preserved byte-for-byte; the installed libpros.a matches the release archive. Brain upload remains pending.
- Windows and Intel macOS packages are built/tested in GitHub Actions; Apple silicon is built/tested locally because the hosted arm64 runner remained queued. Queued redundant jobs are canceled after the local native artifact is verified.


## v1.4.0 — exact kernel identity

- All 24 Python tests passed locally, including nonce/sequence-matched identity acceptance, rejected wrong family/version/build/capabilities, and mandatory verification before arming.
- Native ASan/UBSan tests verify the compiled local identity API, maximum-width request correlation and that identity probes do not renew the watchdog or consume heartbeat sequences. Earlier motor/ADI and watchdog tests remain enabled.
- The build checks source fingerprint, compiled identity header and app expectation for agreement. Native frozen-package dependency/protocol and disconnected GUI smoke tests are part of packaging.
- This identifies the build/version; it is not cryptographic authentication. Physical hardware testing remains pending.


## v1.3.0 — desktop packages and ADI guard

- The 20 Python tests passed locally; Windows and Intel macOS frozen packages passed native CI unit and frozen-executable dependency/protocol smoke tests. Apple silicon packaging is checked separately.
- Native ASan/UBSan tests exercise production ADI setter bodies and the expanded stop routine, including internal/expander PWM neutralization, blocked valve/servo/configuration changes, LED rejection and normal behavior after STOP clears.
- The kernel replaces seven archive members; the additional member is vdml_ext_adi.c.o. Other official PROS 4.2.2 objects remain unchanged. Existing upstream unsigned-comparison warnings in that file do not prevent compilation.
- Hardware USB, ADI/pneumatic behavior and cable removal still require physical validation.


## v1.2.0 — native practice disconnect watchdog

- The state engine and parser passed Clang AddressSanitizer/UndefinedBehaviorSanitizer tests. Watchdog coverage includes the exact 1500 ms deadline, native field bits, native Driver fallback, a latched stop, stale/wrong-session messages, Disabled-only re-arming with a new token, read-only status, explicit stop and uint32 clock rollover.
- All 18 Python tests passed, covering the existing phase timing/Disable queue behavior plus Brain acknowledgement matching, split replies, no command retries, heartbeat before Enable, beats while Disabled, timeout rejection and stop on Disconnect.
- All six overlay objects compiled for Cortex-A9 with ARM GNU 15.2.1. A clean diagnostic project containing the new template linked both cold and hot images. Existing LLEMU deprecation warnings remain.
- The original working Python tester was preserved separately; the new tool is supplied under tools/python-practice-watchdog.
- No live mode activation or cable-pull test was performed for this release. The actual robot project still needs the new kernel applied, rebuilt and uploaded. The release is marked as a prerelease pending hardware validation.
- Installed `kernel@4.2.2-recf.2` from the published GitHub depot into the supplied PROS_RECF_TEST robot project. Its original main.cpp was preserved byte-for-byte, the installed libpros.a matches the published ZIP, and a clean ARM GNU 15.2.1 cold/hot build with liblvgl passed. Hardware upload remains pending because no VEX USB device was detected.
- Coverage and output limitations are documented in [PRACTICE_WATCHDOG.md](PRACTICE_WATCHDOG.md).

## Earlier v1.1.0 validation

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
