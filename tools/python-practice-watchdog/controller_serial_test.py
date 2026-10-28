#!/usr/bin/env python3
"""RECF Field Control: Controller practice phases and Brain heartbeat watchdog."""
import argparse
import binascii
from contextlib import contextmanager
import datetime
import glob
import json
import os
import plistlib
import queue
import math
import secrets
import re
import select
import subprocess
import sys
if os.name != "nt":
    import termios
import threading
import time
from pathlib import Path

APP_VERSION = '1.4.0'
EXPECTED_KERNEL = 'RECF_CONTROL_STATE 4.2.2 1.4.0 98e3505ffe5a3d9f 0000000f'
IS_WINDOWS = os.name == 'nt'

VERSION_QUERY = bytes.fromhex('c9 36 b8 47 a4')


def ports():
    if IS_WINDOWS:
        from serial.tools.list_ports import comports
        names = {0x503: 'VEX Robotics V5 Controller', 0x501: 'VEX Robotics V5 Brain'}
        return sorted([{'port': p.device, 'name': names.get(p.pid, p.description),
                        'vendor': hex(p.vid), 'product': hex(p.pid or 0),
                        'location': p.location or ''}
                       for p in comports() if p.vid == 0x2888],
                      key=lambda p: ('Controller' not in p['name'], p['port']))
    tree = plistlib.loads(subprocess.check_output(['ioreg', '-r', '-c', 'IOUSBHostDevice', '-a', '-l']))
    result = {}
    def walk(node):
        yield node
        for child in node.get('IORegistryEntryChildren', []):
            yield from walk(child)
    for root in tree:
        for device in walk(root):
            name = device.get('USB Product Name', device.get('IORegistryEntryName', ''))
            if device.get('idVendor') != 0x2888 or 'VEX' not in name:
                continue
            for entry in walk(device):
                path = entry.get('IOCalloutDevice')
                if path and os.path.exists(path):
                    result[path] = {'port': path, 'name': name,
                                    'vendor': '0x2888', 'product': hex(device.get('idProduct', 0)),
                                    'location': hex(device.get('locationID', 0))}
    return sorted(result.values(), key=lambda p: ('Controller' not in p['name'], p['port']))


@contextmanager
def open_vex_port(path, emit):
    if path not in {p['port'] for p in ports()}:
        raise ValueError('This is not a current VEX USB port. Click Rescan ports.')
    if IS_WINDOWS:
        import serial
        with serial.Serial(path, baudrate=115200, bytesize=8, parity='N', stopbits=1,
                           timeout=0, write_timeout=1, rtscts=False, dsrdtr=False) as port:
            emit('OPEN', f'{path} — 115200 baud, 8 data bits, no parity, 1 stop bit')
            try:
                yield port
            finally:
                emit('CLOSE', 'Port released.')
        return
    fd = None
    original = None
    try:
        fd = os.open(path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        original = termios.tcgetattr(fd)
        cfg = termios.tcgetattr(fd)
        cfg[0] = cfg[1] = cfg[3] = 0
        cfg[2] = (cfg[2] & ~(termios.CSIZE | termios.PARENB | termios.CSTOPB)) | termios.CS8 | termios.CREAD | termios.CLOCAL
        cfg[4] = cfg[5] = termios.B115200
        cfg[6][termios.VMIN] = cfg[6][termios.VTIME] = 0
        termios.tcsetattr(fd, termios.TCSANOW, cfg)
        emit('OPEN', f'{path} — 115200 baud, 8 data bits, no parity, 1 stop bit')
        yield fd
    finally:
        if fd is not None:
            if original is not None:
                try:
                    termios.tcsetattr(fd, termios.TCSANOW, original)
                except OSError:
                    pass
            os.close(fd)
            emit('CLOSE', 'Port released.')


def readable(fd, timeout):
    if not IS_WINDOWS:
        return bool(select.select([fd], [], [], timeout)[0])
    deadline = time.monotonic() + timeout
    while True:
        if fd.in_waiting:
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(min(0.01, max(0, deadline-time.monotonic())))


def write_packet(fd, packet, emit):
    pending = memoryview(packet)
    deadline = time.monotonic() + 2
    while pending:
        if time.monotonic() >= deadline:
            raise TimeoutError('Serial write did not complete. Delivery is unconfirmed.')
        try:
            count = fd.write(pending) if IS_WINDOWS else os.write(fd, pending)
            if count:
                pending = pending[count:]
            else:
                time.sleep(0.01) if IS_WINDOWS else select.select([], [fd], [], 0.1)
        except BlockingIOError:
            time.sleep(0.01) if IS_WINDOWS else select.select([], [fd], [], 0.1)
    emit('TX', packet.hex(' '))


def read_chunk(fd, emit):
    try:
        data = fd.read(4096) if IS_WINDOWS else os.read(fd, 4096)
    except BlockingIOError:
        return b''
    if data:
        emit('RX', f'{len(data)} bytes | HEX {data.hex(" ")} | TEXT '+''.join(chr(b) if 32 <= b < 127 else '.' for b in data))
    return data


def extract_frames(buffer):
    frames = []
    while True:
        index = buffer.find(b'\xaa\x55')
        if index < 0:
            buffer[:] = buffer[-1:]
            break
        if index:
            del buffer[:index]
        if len(buffer) < 4:
            break
        header = 4
        length = buffer[3]
        if length & 0x80:
            if len(buffer) < 5:
                break
            length = ((length & 0x7f) << 8) | buffer[4]
            header = 5
        if length > 4096:
            del buffer[:2]
            continue
        if len(buffer) < header + length:
            break
        frames.append(bytes(buffer[:header+length]))
        del buffer[:header+length]
    return frames


def probe(path, seconds, passive, emit, stopped=None):
    received = 0
    buffer = bytearray()
    valid = 0
    started = time.monotonic()
    with open_vex_port(path, emit) as fd:
        emit('INFO', 'Passive listening; no bytes sent.' if passive else 'Sending only the read-only VEX system-version query once per second.')
        next_query = 0
        while time.monotonic() - started < seconds and not (stopped and stopped.is_set()):
            now = time.monotonic()
            if not passive and now >= next_query:
                write_packet(fd, VERSION_QUERY, emit)
                next_query = now + 1
            if not readable(fd, 0.1):
                continue
            data = read_chunk(fd, emit)
            received += len(data)
            buffer.extend(data)
            for frame in extract_frames(buffer):
                if frame[:4] == b'\xaa\x55\xa4\x08' and len(frame) == 12:
                    valid += 1
                    emit('REPLY', f'Valid VEX system-version reply ({len(frame)} bytes): {frame.hex(" ")}')
    report = {'port': path, 'received_bytes': received, 'version_replies': valid,
              'duration_seconds': round(time.monotonic()-started, 2), 'passive': passive}
    emit('RESULT', json.dumps(report))
    if valid:
        emit('PASS', 'Computer opened the serial port AND received valid VEX replies.')
    elif received:
        emit('INFO', 'Incoming bytes received, but no complete VEX version reply was identified.')
    else:
        emit('INFO', 'Port opened, but no bytes arrived. A silent passive connection is not proof of failure.')
    return report


def wait_for_reply(fd, command, extended, timeout, emit, stopped=None):
    buffer = bytearray()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if stopped and stopped.is_set():
            raise InterruptedError('Stopped waiting for a reply. The device state is unconfirmed.')
        if not readable(fd, 0.1):
            continue
        buffer.extend(read_chunk(fd, emit))
        for frame in extract_frames(buffer):
            if frame[2] != command:
                continue
            header = 5 if frame[3] & 0x80 else 4
            payload = frame[header:]
            if extended is None:
                if command == 0xa4 and len(payload) != 8:
                    continue
                return frame
            if len(payload) < 4 or payload[0] != extended:
                continue
            if binascii.crc_hqx(frame, 0) != 0:
                emit('INFO', 'Ignoring a reply with an invalid CRC.')
                continue
            ack = payload[1]
            if ack != 0x76:
                reasons = {0xd3:'Program file/slot not found', 0xd5:'Command not supported', 0xce:'Packet CRC rejected', 0xff:'Request rejected'}
                raise RuntimeError(f'{reasons.get(ack,"VEX rejected the command")} (reply 0x{ack:02x}). Check the Controller-to-Brain connection.')
            return frame
    raise TimeoutError('No matching reply received. Result is unconfirmed; check the Brain before retrying.')


MODE_BYTES = {'AUTON': 10, 'DRIVER': 8, 'DISABLED': 11}
PHASE_SECONDS = {'AUTON': 15, 'DRIVER': 105}


def competition_packet(mode, seconds=0):
    if mode not in MODE_BYTES or not isinstance(seconds, int) or not 0 <= seconds <= 0xffffffff:
        raise ValueError('Invalid competition mode or timer')
    payload = bytes([MODE_BYTES[mode]]) + seconds.to_bytes(4, 'little')
    raw = bytes.fromhex('c9 36 b8 47 58 c1') + bytes([len(payload)]) + payload
    return raw + binascii.crc_hqx(raw, 0).to_bytes(2, 'big')


class PracticeSession:
    """One serial owner, timed phases, manual transition to Driver, explicit Disable."""
    def __init__(self, emit, now=time.monotonic, transact=None):
        self.emit = emit
        self.now = now
        self.transact = transact
        self.fd = None
        self.context = None
        self.path = None
        self.enabled = False
        self.mode = 'DISABLED'
        self.last_phase = None
        self.deadline = None
        self.next_update = 0

    @property
    def connected(self):
        return self.fd is not None

    def snapshot(self):
        return {'connected': self.connected, 'path': self.path, 'enabled': self.enabled,
                'mode': self.mode, 'last_phase': self.last_phase,
                'remaining': max(0, self.deadline-self.now()) if self.deadline else 0}

    def publish(self):
        self.emit('CONTROL', self.snapshot())

    def connect(self, path):
        if self.connected:
            raise RuntimeError('Disconnect the current Controller first.')
        device = next((item for item in ports() if item['port'] == path), None)
        if not device or device['product'] != '0x503':
            raise ValueError('Select the V5 Controller USB port, not a Brain port. Click Rescan ports.')
        self.context = open_vex_port(path, self.emit)
        try:
            self.fd = self.context.__enter__()
            self.path = path
            termios.tcflush(self.fd, termios.TCIFLUSH)
            write_packet(self.fd, VERSION_QUERY, self.emit)
            version = wait_for_reply(self.fd, 0xa4, None, 2, self.emit)
            if version[9] != 0x11:
                raise RuntimeError('The selected device did not identify as a V5 Controller.')
            if not version[10] & 2:
                raise RuntimeError('Controller USB works, but it reports no connected Brain. Pair the Controller and Brain first.')
            self.disable()
            self.emit('INFO', 'Controller connected and Disable acknowledged. Select and start your desired program on the Controller, then choose a phase here.')
        except Exception:
            self.release()
            raise

    def send(self, mode, seconds=0):
        if not self.connected:
            raise RuntimeError('Connect the Controller first.')
        packet = competition_packet(mode, seconds)
        if self.transact:
            return self.transact(packet)
        write_packet(self.fd, packet, self.emit)
        return wait_for_reply(self.fd, 0x58, 0xc1, 0.6, self.emit)

    def run(self, mode):
        if mode not in PHASE_SECONDS:
            raise ValueError('Choose Autonomous or Driver.')
        if self.enabled:
            raise RuntimeError('Disable the current phase before starting another.')
        # Anchor the deadline to transmission, not to delayed acknowledgement.
        started = self.now()
        self.send(mode, PHASE_SECONDS[mode])
        self.mode = mode
        self.last_phase = mode
        self.deadline = started + PHASE_SECONDS[mode]
        self.next_update = self.now() + 0.25
        self.enabled = True
        self.emit('ACK', f'{mode} enabled for {PHASE_SECONDS[mode]} seconds.')
        self.publish()

    def disable(self):
        self.send('DISABLED', 0)
        self.enabled = False
        self.mode = 'DISABLED'
        self.deadline = None
        self.emit('ACK', 'Disable acknowledged by the Controller.')
        self.publish()

    def enable(self):
        if not self.last_phase:
            raise RuntimeError('Choose Run Autonomous or Run Driver first. Enable restarts the last chosen phase.')
        self.run(self.last_phase)

    def tick(self):
        if not self.enabled:
            return
        left = self.deadline-self.now()
        if left <= 0:
            phase = self.last_phase
            self.disable()
            self.emit('INFO', 'Autonomous complete — Disabled. Click Run Driver when ready.' if phase == 'AUTON' else 'Driver complete — Disabled.')
        elif self.now() >= self.next_update and left > 0.8:
            self.send(self.mode, math.ceil(left))
            self.next_update = self.now() + 0.25
        self.publish()

    def release(self):
        context = self.context
        self.fd = None
        self.context = None
        self.enabled = False
        self.deadline = None
        if context:
            context.__exit__(None, None, None)
        self.publish()

    def disconnect(self):
        try:
            if self.connected:
                self.disable()
        finally:
            self.release()

    def failed(self, error):
        self.mode = 'UNCONFIRMED'
        self.emit('ERROR', str(error))
        try:
            if self.connected:
                self.disable()
        except Exception as stop_error:
            self.mode = 'UNCONFIRMED'
            self.emit('ERROR', 'Disable could not be confirmed: '+str(stop_error)+'. Check the robot directly.')
        finally:
            self.release()


WATCHDOG_SECONDS = 1.5


def fifo_packet(write=None):
    data = bytes(write) if write is not None else b''
    if len(data) > 224:
        raise ValueError('FIFO write too long')
    payload = bytes([1, len(data) if write is not None else 64]) + data
    length = bytes([len(payload)]) if len(payload) < 128 else bytes([(len(payload) >> 8) | 128, len(payload) & 255])
    raw = bytes.fromhex('c9 36 b8 47 56 27') + length + payload
    return raw + binascii.crc_hqx(raw, 0).to_bytes(2, 'big')


class WatchdogPracticeSession(PracticeSession):
    def __init__(self, emit, now=time.monotonic, transact=None):
        super().__init__(emit, now, transact)
        self.watch_armed = False
        self.kernel_identity = None
        self.watch_token = 0
        self.watch_seq = 0
        self.watch_buffer = ''
        self.last_watch_ack = 0
        self.next_beat = 0

    def watch(self, command):
        if not self.connected:
            raise RuntimeError('Controller is disconnected.')
        self.watch_seq += 1
        seq = self.watch_seq
        line = f'@RECF/1 {seq} {self.watch_token} {command}\n'.encode('ascii')
        write_packet(self.fd, fifo_packet(line), self.emit)
        deadline = self.now() + 0.65
        while self.now() < deadline:
            try:
                packet = wait_for_reply(self.fd, 0x56, 0x27, min(0.12, max(0.01, deadline-self.now())), self.emit)
                header = 5 if packet[3] & 0x80 else 4
                if packet[header+2] == 1:
                    self.watch_buffer += packet[header+3:-2].decode('ascii', errors='ignore')
                    self.watch_buffer = self.watch_buffer[-4096:]
                    while '\n' in self.watch_buffer:
                        incoming, self.watch_buffer = self.watch_buffer.split('\n', 1)
                        if command == 'WATCH_ID':
                            identity = re.fullmatch(r'@RECF/1 (\d+) (\d+) ID (.+)', incoming)
                            if identity and int(identity[1]) == seq and int(identity[2]) == self.watch_token:
                                if identity[3] != EXPECTED_KERNEL:
                                    raise RuntimeError('Kernel identity mismatch. Expected '+EXPECTED_KERNEL+'; received '+identity[3]+'. Enable is blocked.')
                                self.kernel_identity = identity[3]
                                self.emit('KERNEL', 'Verified: '+self.kernel_identity)
                                return
                        m = re.search(r'@RECF/1 (\d+) (\d+) (OK|ERR) (STOP|AUTON|DRIVER) WATCHDOG (\d+) ([A-Z_]+)$', incoming)
                        if not m or int(m[1]) != seq or int(m[2]) != self.watch_token:
                            continue
                        if m[3] != 'OK':
                            raise RuntimeError('Brain watchdog rejected '+command+': '+m[6])
                        expected = {'WATCH_ARM':'ARMED', 'WATCH_BEAT':'HEARTBEAT', 'WATCH_STOP':'STOPPED'}[command]
                        if m[6] != expected:
                            raise RuntimeError('Unexpected Brain watchdog acknowledgement: '+m[6])
                        self.last_watch_ack = self.now()
                        self.next_beat = self.now() + 0.2
                        self.emit('WATCHDOG', 'Brain acknowledged '+command)
                        return
            except TimeoutError:
                pass  # Poll for the Brain's unique reply; never resend the command.
            if self.now() < deadline:
                write_packet(self.fd, fifo_packet(), self.emit)
        raise TimeoutError('No matching Brain watchdog acknowledgement. Install the matching kernel 4.2.2-recf.4 and run the rebuilt program. Enable is blocked.')

    def connect(self, path):
        super().connect(path)
        self.watch_token = secrets.randbits(32) or 1
        self.watch_seq = 0
        self.watch_buffer = ''
        try:
            self.watch('WATCH_ID')
            self.watch('WATCH_ARM')
            self.watch_armed = True
            self.emit('INFO', 'Brain watchdog armed. Disconnect timeout: 1.5 seconds. Select a phase to enable.')
        except Exception as error:
            self.failed(error)
            raise

    def run(self, mode):
        if not self.watch_armed:
            raise RuntimeError('Brain watchdog is not armed. Reconnect before enabling.')
        self.watch('WATCH_BEAT')
        super().run(mode)

    def tick(self):
        if self.connected and self.watch_armed and self.now() >= self.next_beat:
            self.watch('WATCH_BEAT')
        super().tick()

    def release(self):
        self.watch_armed = False
        self.kernel_identity = None
        self.emit('KERNEL', 'Kernel: not verified')
        super().release()

    def disconnect(self):
        error = None
        try:
            if self.connected:
                try:
                    self.disable()
                except Exception as issue:
                    error = issue
                if self.watch_armed:
                    try:
                        self.watch('WATCH_STOP')
                    except Exception as issue:
                        error = error or issue
        finally:
            self.release()
        if error:
            raise error


def gui(smoke_output=None):
    import tkinter as tk
    from tkinter import ttk, filedialog
    root = tk.Tk()
    root.title('RECF Field Control '+APP_VERSION+' — Brain Watchdog')
    root.geometry('1100x760')
    root.minsize(850, 600)
    outer = ttk.Frame(root, padding=18)
    outer.pack(fill='both', expand=True)
    ttk.Label(outer, text='VEX practice control · Brain watchdog', font=('', 22, 'bold')).pack(anchor='w')
    ttk.Label(outer, text='Start your rebuilt watchdog-enabled program on the Controller BEFORE connecting here. Brain heartbeat acknowledgement is required.').pack(anchor='w', pady=(4, 12))
    events = queue.Queue()
    commands = queue.PriorityQueue()
    counter = 0
    generation = 0
    choices = {}
    selection = tk.StringVar()
    kernel_status = tk.StringVar(value='Kernel: not verified')
    status = tk.StringVar(value='Select the Controller USB port, then Connect Controller.')
    timer = tk.StringVar(value='00:00.0')
    phase_label = tk.StringVar(value='Disconnected')
    enabled_var = tk.BooleanVar(value=False)
    state = {'connected': False, 'enabled': False, 'last_phase': None, 'mode': 'DISABLED', 'remaining': 0}
    busy = False
    closing = False
    probe_stop = threading.Event()
    log_lines = []

    def emit(kind, message):
        events.put((kind, message))

    def submit(action, value=None):
        nonlocal counter, busy, generation
        if action in ('DISABLE', 'DISCONNECT', 'QUIT'):
            generation += 1
            probe_stop.set()
        elif busy:
            return
        if action == 'PROBE':
            probe_stop.clear()
        busy = True
        counter += 1
        commands.put((0 if action in ('DISABLE', 'DISCONNECT', 'QUIT') else 1, counter, action, value, generation))
        refresh_controls()

    session = WatchdogPracticeSession(emit)

    def worker():
        while True:
            try:
                _, _, action, value, token = commands.get(timeout=0.05)
            except queue.Empty:
                try:
                    session.tick()
                except Exception as error:
                    session.failed(error)
                continue
            try:
                if action in ('AUTON', 'DRIVER', 'ENABLE', 'PROBE') and token != generation:
                    continue
                if action == 'CONNECT': session.connect(value)
                elif action == 'AUTON': session.run('AUTON')
                elif action == 'DRIVER': session.run('DRIVER')
                elif action == 'DISABLE':
                    if session.connected: session.disable()
                elif action == 'ENABLE': session.enable()
                elif action == 'DISCONNECT': session.disconnect()
                elif action == 'PROBE':
                    if session.connected: raise RuntimeError('Disconnect practice control before testing another port.')
                    probe(value, 10, False, emit, probe_stop)
                elif action == 'QUIT':
                    session.disconnect()
                    return
            except Exception as error:
                if action in ('CONNECT', 'PROBE') and not session.enabled:
                    emit('ERROR', str(error))
                else:
                    session.failed(error)
            finally:
                events.put(('DONE', action))

    row = ttk.Frame(outer)
    row.pack(fill='x')
    picker = ttk.Combobox(row, textvariable=selection, state='readonly', width=90)
    picker.pack(side='left', fill='x', expand=True)
    def refresh():
        try:
            current = ports()
            previous = selection.get()
            choices.clear()
            for item in current:
                choices[f'{item["name"]} | {item["port"]} | PID {item["product"]}'] = item['port']
            picker['values'] = list(choices)
            selection.set(previous if previous in choices else next(iter(choices), 'No VEX USB device found'))
            emit('PORTS', json.dumps(current))
        except Exception as error:
            emit('ERROR', str(error))
    rescan = ttk.Button(row, text='Rescan ports', command=refresh)
    rescan.pack(side='left', padx=(10, 0))
    def connect():
        path = choices.get(selection.get())
        if not path:
            emit('ERROR', 'Choose a current Controller port first.')
            return
        submit('CONNECT', path)
    link_row = ttk.Frame(outer)
    link_row.pack(fill='x', pady=12)
    connect_button = ttk.Button(link_row, text='Connect Controller', command=connect)
    connect_button.pack(side='left')
    disconnect_button = ttk.Button(link_row, text='Disconnect', command=lambda: submit('DISCONNECT'))
    disconnect_button.pack(side='left', padx=8)
    test_button = ttk.Button(link_row, text='Test serial (10 s)', command=lambda: submit('PROBE', choices.get(selection.get())))
    test_button.pack(side='left')
    ttk.Button(link_row, text='End serial test', command=probe_stop.set).pack(side='left', padx=8)

    phase_box = ttk.LabelFrame(outer, text='Practice phases', padding=16)
    phase_box.pack(fill='x', pady=(0, 12))
    heading = ttk.Frame(phase_box)
    heading.pack(fill='x')
    ttk.Label(heading, textvariable=phase_label, font=('', 16, 'bold')).pack(side='left')
    ttk.Label(heading, textvariable=timer, font=('Menlo', 30, 'bold')).pack(side='right')
    buttons = ttk.Frame(phase_box)
    buttons.pack(fill='x', pady=(12, 8))
    auton_button = ttk.Button(buttons, text='Run Autonomous — 15 seconds', command=lambda: submit('AUTON'))
    auton_button.pack(side='left', fill='x', expand=True)
    driver_button = ttk.Button(buttons, text='Run Driver — 1 minute 45 seconds', command=lambda: submit('DRIVER'))
    driver_button.pack(side='left', fill='x', expand=True, padx=(12, 0))
    toggle_row = ttk.Frame(phase_box)
    toggle_row.pack(fill='x', pady=(6, 0))
    def toggle():
        desired = enabled_var.get()
        enabled_var.set(state['enabled'])
        if desired and not state.get('last_phase'):
            emit('INFO', 'Choose Run Autonomous or Run Driver first. The toggle can then restart that phase.')
            return
        submit('ENABLE' if desired else 'DISABLE')
    toggle_button = ttk.Checkbutton(toggle_row, text='Enable / Disable', variable=enabled_var, command=toggle)
    toggle_button.pack(side='left')
    disable_button = ttk.Button(toggle_row, text='Disable now', command=lambda: submit('DISABLE'))
    disable_button.pack(side='right')
    ttk.Label(phase_box, text='Each phase ends in Disabled. Driver starts only when you click Run Driver. Enable restarts the last phase.').pack(anchor='w', pady=(10, 0))
    ttk.Label(outer, textvariable=kernel_status, wraplength=1020).pack(anchor='w', pady=(0, 6))
    ttk.Label(outer, textvariable=status, wraplength=1020).pack(anchor='w', pady=(0, 8))
    frame = ttk.Frame(outer)
    frame.pack(fill='both', expand=True)
    text = tk.Text(frame, wrap='word', font=('Menlo', 11), state='disabled')
    scroll = ttk.Scrollbar(frame, command=text.yview)
    text.configure(yscrollcommand=scroll.set)
    scroll.pack(side='right', fill='y')
    text.pack(fill='both', expand=True)
    def save():
        path = filedialog.asksaveasfilename(defaultextension='.txt', initialfile='vex-practice-log.txt')
        if path: Path(path).write_text('\n'.join(log_lines)+'\n')
    ttk.Button(outer, text='Save log', command=save).pack(anchor='e', pady=(8, 0))

    def refresh_controls():
        connected = state['connected']
        picker['state'] = 'disabled' if connected or busy else 'readonly'
        rescan['state'] = connect_button['state'] = test_button['state'] = 'disabled' if connected or busy else 'normal'
        disconnect_button['state'] = 'normal' if connected else 'disabled'
        auton_button['state'] = driver_button['state'] = 'normal' if connected and not state['enabled'] and not busy else 'disabled'
        toggle_button['state'] = 'normal' if connected and (state['enabled'] or not busy) else 'disabled'
        disable_button['state'] = 'normal' if connected else 'disabled'
        enabled_var.set(state['enabled'])

    def pump():
        nonlocal busy
        while True:
            try: kind, message = events.get_nowait()
            except queue.Empty: break
            if kind == 'KERNEL':
                kernel_status.set(message)
            if kind == 'CONTROL':
                state.update(message)
                remaining = state['remaining']
                timer.set(f'{int(remaining//60):02d}:{remaining%60:04.1f}')
                phase_label.set(('Autonomous' if state['mode'] == 'AUTON' else 'Driver') if state['enabled'] else ('Disabled' if state['connected'] else 'Disconnected / unconfirmed' if state['mode'] == 'UNCONFIRMED' else 'Disconnected'))
                refresh_controls()
                continue
            if kind == 'DONE':
                busy = not commands.empty()
                refresh_controls()
                if closing and message == 'QUIT':
                    root.destroy()
                    return
                continue
            line = f'{datetime.datetime.now():%H:%M:%S} [{kind}] {message}'
            log_lines.append(line)
            text['state'] = 'normal'
            text.insert('end', line+'\n')
            text.see('end')
            text['state'] = 'disabled'
            if kind in ('ACK', 'INFO', 'ERROR', 'PASS'): status.set(message)
        root.after(60, pump)

    def close():
        nonlocal closing
        if closing: return
        closing = True
        status.set('Sending Disable and closing the serial port…')
        submit('QUIT')
    root.protocol('WM_DELETE_WINDOW', close)
    refresh()
    refresh_controls()
    threading.Thread(target=worker, daemon=True).start()
    pump()
    if smoke_output:
        def finish_smoke():
            smoke_output.write_text(json.dumps({'version': APP_VERSION, 'title': root.title(),
                'kernel_status': kernel_status.get(), 'connected': session.connected,
                'controls': [auton_button.cget('text'), driver_button.cget('text'), disable_button.cget('text')]}))
            root.destroy()
        root.after(300, finish_smoke)
    root.mainloop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gui-smoke-test-output', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--self-test-output', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--list', action='store_true', help='List USB device-to-port mappings')
    parser.add_argument('--port', help='Probe a specific current VEX port; otherwise open the GUI')
    parser.add_argument('--seconds', type=float, default=3)
    parser.add_argument('--passive', action='store_true', help='Listen without sending the version query')
    args = parser.parse_args()
    if args.gui_smoke_test_output:
        gui(args.gui_smoke_test_output)
    elif args.self_test_output:
        import tkinter
        import serial
        args.self_test_output.write_text(json.dumps({'app_version': APP_VERSION,
            'platform': sys.platform, 'tk': tkinter.TkVersion, 'serial': serial.__version__,
            'auton_packet': competition_packet('AUTON', 15).hex(),
            'watchdog_seconds': WATCHDOG_SECONDS, 'expected_kernel': EXPECTED_KERNEL}))
    elif args.list:
        print(json.dumps(ports(), indent=2))
    elif args.port:
        if not 0 < args.seconds <= 600:
            parser.error('--seconds must be greater than zero and at most 600')
        try:
            emit = lambda k,m: print(f'[{k}] {m}', flush=True)
            probe(args.port, args.seconds, args.passive, emit)
        except Exception as error:
            print(f'[ERROR] {type(error).__name__}: {error}', flush=True)
            raise SystemExit(1)
    else:
        gui()
