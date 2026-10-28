# RECF Field Control v1.4.0 — combined Controller + heartbeat app

Download the native macOS or Windows app from [the release](https://github.com/Offbrand-Window/RECF_Field_Control/releases/tag/v1.4.0); no Python installation is required. See [desktop setup](../../DESKTOP_APP.md). The source launcher below is optional for development. This release requires its exact matching kernel identity; v1.3.0 remains separately available for older heartbeat kernels.

The original working Python version is preserved in `Controller Serial Test` and in the saved working-version ZIP. This separate edition requires a heartbeat acknowledgement from the Brain before enabling either timed phase.

## Install on the robot first

Apply `kernel@4.2.2-recf.4` from RECF_Control_State v1.4.0 to the existing PROS robot project, rebuild, and upload that program. A Python-only change cannot stop a Brain after the USB cable is gone. The new kernel must be part of the program actually running on the Brain.

In the robot project's terminal:

```sh
pros c add-depot recf-control-state "https://raw.githubusercontent.com/Offbrand-Window/RECF_Field_Control/develop-pros-4/depot.json"
pros c apply kernel@4.2.2-recf.4 --depot recf-control-state --force-apply --force
pros make
```

Upload using your normal project workflow. This upgrade does not replace your robot routines. Start the rebuilt program using the Controller before connecting the watchdog tool. The native-practice watchdog does not require `recf_control_enable(true)`; it is armed only by this tool's explicit handshake after program initialization. The older software-mode-selection feature remains separate.

## Use

1. Start your rebuilt robot program on the Controller and leave the Controller paired to the Brain.
2. Connect the Controller to the Mac by USB.
3. Open **Open Watchdog Practice.command**, rescan, choose the Controller, and connect.
4. The tool requests native Disabled, verifies the compiled kernel identity matches its expected version/build/capabilities, then arms the Brain watchdog and waits for the Brain's nonce-matched acknowledgement.
5. Run Autonomous (15 seconds), then manually run Driver (105 seconds). Enable/Disable retains the working version's controls.

Python sends heartbeats approximately every 200 ms. If the Brain receives no fresh valid heartbeat for 1.5 seconds, the kernel forces Disabled and latches that state. Removing the computer's USB cable, closing or freezing Python, or losing the Controller-to-Brain route all stop heartbeat delivery. Reconnecting does not automatically resume motion: the Controller must first report Disabled, and a fresh session must be armed.

Normal Disconnect also requests a latched Brain stop. A VEX USB packet ACK alone is insufficient: the tool requires the matching application-level WATCHDOG reply from the Brain. If the kernel is old, the program is not ready, or the FIFO link cannot carry the heartbeat, the tool refuses Enable. There is no fallback to unguarded timed operation in this edition.

## Coverage and limits

The kernel stops its managed autonomous/driver task, exposes Disabled to normal PROS competition predicates, zeros smart motors, and blocks nonzero commands through the patched standard smart-motor APIs while the watchdog is tripped. The latch remains active even when native field-connected bits disappear or underlying physical mode becomes Driver.

Independently created tasks are not deleted. The ADI guard blocks new standard PROS valve/servo/analog output changes and neutralizes PWM motors. It holds valve state and cannot cancel a cylinder stroke already underway. Direct VEX SDK writes and other unpatched outputs need explicit application handling. This is not a firmware-level hardware emergency stop. The 1.5-second bound assumes the Brain's scheduler and system daemon are running normally.

Source and simulated tests are supplied. Before normal use, verify cable removal during both phases with the robot secured and confirm its actual outputs stop. No live autonomous/driver activation was performed while implementing this change.
