import binascii
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('tester', Path(__file__).with_name('controller_serial_test.py'))
tester = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tester)


def response(extended=0xc1, ack=0x76):
    raw = bytes([0xaa, 0x55, 0x58, 4, extended, ack])
    return raw + binascii.crc_hqx(raw, 0).to_bytes(2, 'big')


class PracticeTests(unittest.TestCase):
    def session(self):
        self.clock = 100.0
        self.sent = []
        self.events = []
        s = tester.PracticeSession(lambda *args: self.events.append(args), now=lambda: self.clock, transact=self.sent.append)
        s.fd = 123  # Synthetic transport only. No OS port is opened by these tests.
        return s

    def test_packet_vectors_match_existing_vex_codec(self):
        expected = {'AUTON': (15, 'c936b84758c1050a0f0000004692'),
                    'DRIVER': (105, 'c936b84758c10508690000007c5a'),
                    'DISABLED': (0, 'c936b84758c1050b00000000382d')}
        for mode, (seconds, data) in expected.items():
            packet = tester.competition_packet(mode, seconds)
            self.assertEqual(packet.hex(), data)
            self.assertEqual(binascii.crc_hqx(packet, 0), 0)

    def test_autonomous_disables_at_15_seconds_and_never_starts_driver(self):
        s = self.session()
        s.run('AUTON')
        self.assertTrue(s.enabled)
        self.clock = 114.99
        s.tick()
        self.assertTrue(s.enabled)
        self.clock = 115
        s.tick()
        self.assertFalse(s.enabled)
        self.assertEqual(s.mode, 'DISABLED')
        self.assertEqual(self.sent[-1], tester.competition_packet('DISABLED'))
        self.assertNotIn(8, [p[7] for p in self.sent])
        before = len(self.sent)
        self.clock = 200
        s.tick()
        self.assertEqual(len(self.sent), before)

    def test_driver_is_manual_and_disables_after_105_seconds(self):
        s = self.session()
        s.run('DRIVER')
        self.clock = 204.99
        s.tick()
        self.assertTrue(s.enabled)
        self.clock = 205
        s.tick()
        self.assertFalse(s.enabled)
        self.assertEqual(s.mode, 'DISABLED')

    def test_enable_restarts_last_phase_and_disable_stops_early(self):
        s = self.session()
        with self.assertRaisesRegex(RuntimeError, 'Choose Run'):
            s.enable()
        s.run('AUTON')
        self.clock = 104
        s.disable()
        self.assertFalse(s.enabled)
        self.assertIsNone(s.deadline)
        self.clock = 109
        s.enable()
        self.assertTrue(s.enabled)
        self.assertEqual(s.deadline, 124)

    def test_running_phase_cannot_be_switched_without_disable(self):
        s = self.session()
        s.run('AUTON')
        with self.assertRaisesRegex(RuntimeError, 'Disable'):
            s.run('DRIVER')

    def test_failed_enable_does_not_claim_enabled(self):
        s = self.session()
        def reject(packet):
            raise TimeoutError('No ACK')
        s.transact = reject
        with self.assertRaises(TimeoutError):
            s.run('AUTON')
        self.assertFalse(s.enabled)
        self.assertIsNone(s.deadline)

    def test_disable_failure_is_not_reported_disabled(self):
        s = self.session()
        s.run('AUTON')
        def reject(packet):
            raise TimeoutError('Unplugged')
        s.transact = reject
        s.failed(RuntimeError('Link lost'))
        self.assertFalse(s.connected)
        self.assertEqual(s.mode, 'UNCONFIRMED')
        self.assertTrue(any('Disable could not be confirmed' in str(e) for e in self.events))

    def test_controller_only_preflight_rejects_brain_ports(self):
        s = tester.PracticeSession(lambda *a: None)
        with patch.object(tester, 'ports', return_value=[{'port': '/fake/brain', 'product': '0x501'}]):
            with self.assertRaisesRegex(ValueError, 'Controller'):
                s.connect('/fake/brain')

    def test_fragmented_and_coalesced_ack_frames(self):
        frame = response()
        buf = bytearray(b'noise\xaa')
        self.assertEqual(tester.extract_frames(buf), [])
        buf.extend(frame[1:4])
        self.assertEqual(tester.extract_frames(buf), [])
        buf.extend(frame[4:]+frame)
        self.assertEqual(tester.extract_frames(buf), [frame, frame])

    def test_crc_and_extended_command_must_match(self):
        good = response()
        bad = good[:-1] + bytes([good[-1] ^ 1])
        with patch.object(tester, 'readable', return_value=True), patch.object(tester, 'read_chunk', return_value=bad+response(0xc2)+good):
            self.assertEqual(tester.wait_for_reply(123, 0x58, 0xc1, 1, lambda *a: None), good)

    def test_nack_is_not_success(self):
        with patch.object(tester, 'readable', return_value=True), patch.object(tester, 'read_chunk', return_value=response(ack=0xff)):
            with self.assertRaisesRegex(RuntimeError, 'rejected'):
                tester.wait_for_reply(123, 0x58, 0xc1, 1, lambda *a: None)


if __name__ == '__main__':
    unittest.main()
