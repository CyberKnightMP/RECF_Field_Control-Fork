# Native practice disconnect watchdog — v1.2.0

This feature protects the Python practice controller's native competition-mode commands. It is independent of the original software mode selector.

The Brain must run a rebuilt program containing `kernel@4.2.2-recf.2`. The watchdog is inactive until an explicit WATCH_ARM handshake succeeds after initialization while physical/native mode is Disabled. A matching WATCH_BEAT renews a 1500 ms Brain-clock lease. The Python tool sends beats approximately every 200 ms and requires a fresh matching Brain acknowledgement before enabling a phase.

On timeout, effective competition status is forced Disabled regardless of native connected/mode bits. The system daemon removes the managed mode task, zeros smart motors, and the patched movement APIs suppress nonzero writes. Stop is latched. Native Driver fallback, late beats, old tokens, stale sequences, and read-only status probes cannot release or renew the latch. Re-arming requires native Disabled and a new session token. WATCH_STOP latches immediately; the protocol has no remote unguarded-disarm command.

The watchdog state is separate from `recf_core_t`, so enabling/disabling the older software selector does not reset it. No initialization API opt-in is required for this native-practice guard: the verified host handshake is the opt-in. A program restart resets the guard; connect the tool to the running rebuilt program before enabling practice phases.

## Protocol

All lines retain the reserved `@RECF/1 <sequence> <session> <command>\n` framing. Session and sequence are nonzero uint32 values. Accepted beats require increasing sequences. Commands are WATCH_ARM, WATCH_BEAT, WATCH_STATUS and WATCH_STOP. Replies use:

```
@RECF/1 <sequence> <session> OK|ERR STOP|AUTON|DRIVER WATCHDOG <raw> <reason>
```

Only WATCH_ARM and accepted WATCH_BEAT renew the lease. WATCH_STATUS is read-only. The new Python tool uses VEX stdio FIFO channel 1 to carry these messages; a transport-level VEX ACK is not a Brain watchdog acknowledgement.

## Installation and Python tool

See [tools/python-practice-watchdog/README.md](tools/python-practice-watchdog/README.md). The original working unguarded Python edition is preserved separately by the workspace backup; it is not made disconnect-safe by installing this kernel alone. Use the watchdog edition and confirm its Brain handshake.

## Limits

Coverage is the managed PROS autonomous/driver task and patched standard smart-motor APIs. User child tasks, direct SDK output, ADI, pneumatics and other nonmotor outputs require application handling. This is not a firmware/hardware emergency stop. Scheduler operation is required. Hardware cable-pull validation remains necessary after rebuilding and uploading the actual robot program.
