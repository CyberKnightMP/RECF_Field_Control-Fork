# RECF Field Control desktop app

One application contains the Controller connection, phase timers and Brain heartbeat sender. No separate Python installation or heartbeat process is required.

## Downloads and opening

Use the ZIP for your platform from the matching GitHub release:

- macOS Apple silicon: `macos-arm64.zip`, containing one `RECF Field Control.app`.
- macOS Intel: `macos-x64.zip`, containing the same app for Intel Macs.
- Windows x64: `windows-x64.zip`, containing one `RECF Field Control.exe`.

Extract the ZIP before opening the app. Builds have no Apple Developer ID/notarization or Windows Authenticode certificate. The operating system may require its normal explicit approval to open a downloaded application. These are native packages, not cross-compiled executables.

Install the matching RECF kernel in the robot project, rebuild and upload it first. Start that program from the Controller, pair the Controller to the Brain, connect Controller USB to the computer, and close any other serial application. Then Connect in RECF Field Control. It requests Disabled and waits for the Brain handshake before allowing Enable.

Run Autonomous lasts 15 seconds. Driver is manually started and lasts 105 seconds. Both finish Disabled. Enable restarts the last selected phase; Disable stops it. Heartbeats are sent by the same background worker even while Disabled. Missing heartbeats trip the Brain watchdog after 1.5 seconds and latch Disabled. Reconnection does not restart motion.

v1.3.0 uses the existing watchdog handshake and works with kernel 4.2.2-recf.2 or newer. Use kernel 4.2.2-recf.3 to add ADI output blocking. The separate v1.4.0 release adds strict kernel identity verification and requires its matching kernel.

## Reproducible packaging

On the target OS with Python 3.13+ and Tk available:

```sh
python -m pip install -r tools/python-practice-watchdog/requirements-build.txt
python -m unittest discover -s tools/python-practice-watchdog -p 'test_*.py'
python tools/build_practice_app.py
```

The build script freezes Python/Tk/pyserial, launches the actual frozen executable for a non-actuating dependency/protocol smoke test, and produces a ZIP plus build/hash manifest. v1.4.0 additionally creates and closes the actual disconnected GUI in a frozen-executable smoke test. macOS uses one .app bundle; Windows uses a single-file .exe. The GitHub Actions workflow builds on macOS arm64, macOS Intel and Windows. Serial hardware and actual cable removal need a separate physical test.
