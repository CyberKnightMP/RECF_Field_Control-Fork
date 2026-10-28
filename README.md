# RECF_Control_State

An opt-in adaptation of PROS V5 that selects the existing `autonomous()`, `opcontrol()`, and `disabled()` callbacks from physical competition control or acknowledged desktop messages.

## Deliverables

- `dist/kernel@4.2.1-recf.1.zip`: installable PROS kernel template, built from the official 4.2.1 binary archive with six modified/new ARM objects. The corresponding upstream files on develop-pros-4 differ from release 4.2.1 only in copyright comments.
- `examples/recf_control/main.cpp`: a diagnostic program displaying the selected mode on the Brain, without moving motors or requiring LVGL.
- `tools/build_recf.py`: reproducible overlay build using an existing VEX C++ SDK and ARM GNU toolchain.
- `tests/recf/`: native state/parser tests and a trace driver used to compare the desktop simulator to the C implementation.
- **RECF Field Control** is the companion desktop application; this repository and release contain the PROS adaptation.

## Install in a PROS project

Use a copy of a PROS 4.2.1 project for the first hardware test. This release uses the current text protocol v1; binary bit-mask messages are not part of this version.

### Install directly from this GitHub repository

Run these commands in the PROS terminal inside the test project:

```sh
pros c add-depot recf-control-state "https://raw.githubusercontent.com/Offbrand-Window/RECF_Control_State/develop-pros-4/depot.json"
pros c apply kernel@4.2.1-recf.1 --depot recf-control-state --force-apply --force
```

The depot downloads the versioned release ZIP and applies it as the project's kernel.

### Or download and apply the ZIP manually

Download [kernel@4.2.1-recf.1.zip](https://github.com/Offbrand-Window/RECF_Control_State/releases/download/v1.0.0/kernel%404.2.1-recf.1.zip) from [the release](https://github.com/Offbrand-Window/RECF_Control_State/releases/tag/v1.0.0). Then run:

```sh
pros c fetch "/absolute/path/to/kernel@4.2.1-recf.1.zip"
pros c apply kernel@4.2.1-recf.1 --force-apply --force --no-download
```

Download SHA-256 checksums and the build manifest are attached to the same release.

The template preserves existing user source files. Add this to the project's existing `initialize()`:

```cpp
pros::c::recf_control_enable(true);
```

Alternatively, replace `src/main.cpp` in a fresh test project with `examples/recf_control/main.cpp`. Then build and upload using the project's normal PROS workflow:

```sh
pros make clean
pros make
pros upload
```

An unmodified robot project does not accept software mode commands. The new header is included by `api.h`. Keep custom-kernel projects on this template: applying a stock kernel replaces these changes. To restore stock behavior, apply the official 4.2.1 kernel and remove the enable call.

## Desktop test

1. Start the diagnostic robot program.
2. Pair the primary Controller with the Brain.
3. Connect the computer's USB cable only to the Controller's micro-B port, leaving the Brain USB disconnected. A direct Brain USB connection is also supported as a separate control test.
4. Open RECF Field Control and choose **Connect via USB**, then select the V5 device. Close any other terminal using that port.
5. A successful connection requires a matching `STATUS` reply from this kernel; USB discovery alone is not success.
6. Choose **Take software control**. The robot first selects STOP.
7. Choose Autonomous, Driver control, or Stop and confirm the Brain's screen changes accordingly. The diagnostic does not move motors.
8. Disconnect USB during an active software mode. After 1.5 seconds without a valid heartbeat, the kernel selects STOP. Reconnecting requires a fresh claim.
9. Connect physical competition control: it takes priority, invalidates the software session, and follows the physical field. Disconnecting that field does not restore an old software run command.

## Behavior

- Disabled by default: existing programs retain PROS's original physical/default behavior.
- Physical competition control has full priority, including when physically enabled. Physical disabled status is never cleared by a software command.
- Software commands are accepted only after `initialize()` finishes.
- `competition_get_status()`, the C predicate functions and their C++ wrappers report the effective selected mode. Connected/field-system bits remain physical. `recf_control_get_physical_status()` returns the unmodified firmware value.
- Selecting a new mode deletes the previous managed mode task and starts the existing callback for that mode. Autonomous restarts from its beginning; pause/resume is not implemented. Repeating the same active mode does not restart its callback.
- STOP and heartbeat expiry select `disabled()`. Smart-motor commands are zeroed on software transitions and repeatedly during software STOP. PROS smart-motor movement APIs also suppress nonzero commands while software STOP is active, including commands from surviving child tasks.
- Child tasks are not automatically deleted. Non-motor outputs (for example pneumatics), ADI PWM/servos, and direct VEX SDK calls need application-specific handling. This is software coordination, not a firmware-level competition-disable replacement.
- **Return to physical control** sends STOP and then RELEASE. With no physical field connected, stock PROS normally selects driver control, so the app reports that result explicitly.
- The desktop timed match runs Auton → STOP → Driver → STOP. Desktop scheduling is not a precision field clock; loss of the desktop heartbeat selects STOP.

## Wire protocol v1

ASCII records ending in LF, under 96 bytes:

```text
@RECF/1 <sequence> <session> <command>

```

Sequence and session are decimal nonzero uint32 values. Commands: STATUS, HELLO, PING, STOP, AUTON, DRIVER, RELEASE. STATUS is read-only. HELLO claims a fresh session into STOP. Movement commands and PING must use the current session with strictly increasing sequence numbers. Valid commands renew the 1500 ms lease; STATUS, stale or invalid commands do not. Duplicate HELLO does not reset an active session. Sessions are coordination tokens, not authentication.

Replies are raw ASCII records, independent of PROS's COBS logging setting:

```text
@RECF/1 <sequence> <session> OK|ERR STOP|AUTON|DRIVER FIELD|SOFTWARE|PHYSICAL <raw-status> <reason>

```

A reply confirms that the mode was selected by the control engine; the system daemon applies that selection on its next iteration. It does not verify physical motor motion. Responses from unrelated or stale requests are ignored by the app. Ordinary serial input is forwarded to PROS's original parser; only the reserved prefix is consumed. Incomplete frames expire after a 500 ms inter-byte gap; overlong/binary frames are discarded.

## Source map

- `src/system/recf_control_core.c`: deterministic mode arbitration, sessions, parser and lease expiry.
- `src/system/recf_control_state.c`: scheduler-safe state access, serial replies, physical status and smart-motor stopping.
- `src/devices/controller.c`: effective status supplied to the existing PROS API.
- `src/system/system_daemon.c`: normal callback selection, source transitions and motor stopping.
- `src/system/dev/ser_daemon.c`: reserved-message interception before the stock input parser.
- `src/devices/vdml_motors.c`: movement commands honor software STOP.
- `include/pros/recf_control_state.h`: public opt-in API.

## Build and validation

See `VALIDATION.md` for actual checks and remaining hardware validation. The private libv5rts submodule is not needed for the supplied overlay build. It compiles the six changed/new objects against locally supplied, ABI-patched VEX headers and replaces matching members in the official stock archive. Remaining kernel and VEX SDK objects are retained unchanged. The public VEX SDK is not redistributed here.

```sh
python3 tools/build_recf.py --sdk /path/to/vexv5 --toolchain /path/to/arm-toolchain/bin --base /path/to/kernel-4.2.1.zip
python3 tests/recf/run_native.py
```

The prebuilt template and diagnostic have been compiled and linked, but have not been uploaded to or verified on a physical V5 Controller/Brain in this session.

Upstream base: https://github.com/purduesigbots/pros/tree/c0897ad1f70950ea7590424d4527ea7af7d32e51
Stock binary: https://github.com/purduesigbots/pros/releases/tag/4.2.1
Firmware adaptation: MPL-2.0, as covered by the upstream LICENSE.

## Upstream PROS

This repository is a fork of [Purdue SIGBots PROS](https://github.com/purduesigbots/pros), based on `develop-pros-4` at `c0897ad1f70950ea7590424d4527ea7af7d32e51`. [Original upstream README](README_UPSTREAM.md).
