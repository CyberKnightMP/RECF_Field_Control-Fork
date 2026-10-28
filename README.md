# RECF Field Control

RECF Field Control now contains the PROS V5 kernel adaptation and the Python practice controller. This repository was previously named **RECF_Control_State**. The former Electron desktop application is discontinued and preserved in [RECF_Field_Control_Legacy](https://github.com/Offbrand-Window/RECF_Field_Control_Legacy).

## Desktop app releases

The combined Controller + heartbeat application is packaged for macOS Apple silicon, macOS Intel and Windows x64. See [downloads and setup](DESKTOP_APP.md). v1.3.0 adds native app packages and [ADI/pneumatic output blocking](ADI_WATCHDOG.md). The separate v1.4.0 release adds kernel identity verification.

## Downloads

Download the [v1.2.0 kernel and Python watchdog tester](https://github.com/Offbrand-Window/RECF_Field_Control/releases/tag/v1.2.0):

- `kernel@4.2.2-recf.2.zip`: PROS 4.2.2 kernel with the native-practice disconnect watchdog.
- `RECF-Python-Practice-Watchdog-v1.2.0.zip`: Python tester with Run Autonomous (15 seconds), Run Driver (105 seconds), and Enable/Disable.
- Build manifest, source patch and SHA-256 checksums accompany the release.

The kernel package and C API retain their existing names for compatibility. Existing `RECF_Control_State` repository links redirect here. The depot name `recf-control-state` remains valid.

## Install and use

In your existing robot project's PROS terminal:

```sh
pros c add-depot recf-control-state "https://raw.githubusercontent.com/Offbrand-Window/RECF_Field_Control/develop-pros-4/depot.json"
pros c apply kernel@4.2.2-recf.2 --depot recf-control-state --force-apply --force
pros make clean
pros make
```

Upload the rebuilt project to the Brain using your normal PROS workflow, selecting the intended program slot. Applying the kernel on the computer alone does not update the Brain. Existing user source files are preserved; do not add `--upgrade-user-files`.

Start the rebuilt program from the Controller, then open `Open Watchdog Practice.command` on macOS and connect to the Controller's USB port. The tester requests Disabled and requires a matching Brain watchdog acknowledgement before enabling either timed phase. Driver starts only when you click Run Driver. No `recf_control_enable(true)` call is needed for this native practice workflow.

For full setup, connection steps, and hardware checks, see the [Python tester guide](tools/python-practice-watchdog/README.md).

## Disconnect behavior

The tester sends heartbeats approximately every 200 ms. After 1.5 seconds without a fresh valid heartbeat, the Brain forces Disabled, stops its managed autonomous/driver callback, zeros smart motors and blocks nonzero commands through the patched standard PROS smart-motor APIs. The stop stays latched after reconnection or native Driver fallback. A fresh session while Disabled is required before enabling again.

The original working tester does not send these heartbeats and does not arm the guard. Use the watchdog edition with the rebuilt robot program. A program restart resets the opt-in guard; establish its handshake before enabling practice phases.

Hardware cable-pull validation is still pending. Secure the robot and verify disconnect behavior in both phases before normal use. Direct SDK calls, ADI/pneumatic outputs and separately created tasks require application-specific handling. This is not a firmware/hardware emergency stop.

## Source and validation

- [Watchdog protocol and limitations](PRACTICE_WATCHDOG.md)
- [Validation record](VALIDATION.md)
- [Repository migration notes](REPOSITORY_MIGRATION.md)
- `tools/build_recf.py`: builds the overlay from the official PROS 4.2.2 archive using ARM GNU 15.2.1 and a local VEX SDK.
- `tests/recf/`: C state/parser/watchdog and smart-motor tests.
- `tools/python-practice-watchdog/`: Python tester source, launcher and 18 tests.

```sh
python3 tests/recf/run_native.py
python3 -m unittest discover -s tools/python-practice-watchdog -p 'test_*.py'
```

The older software mode-selector API remains available separately. It requires `pros::c::recf_control_enable(true)` in initialization; its protocol and physical-field priority are unchanged. The discontinued Electron app is retained only in the legacy archive.
