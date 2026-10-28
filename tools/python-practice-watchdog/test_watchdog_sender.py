import importlib.util
import unittest
import binascii
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('guard_tester',Path(__file__).with_name('controller_serial_test.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def fifo_reply(text):
    payload=bytes([0x27,0x76,1])+text.encode('ascii')
    raw=bytes([0xaa,0x55,0x56,len(payload)+2])+payload
    return raw+binascii.crc_hqx(raw,0).to_bytes(2,'big')

class WatchdogSenderTests(unittest.TestCase):
    def session(self):
        self.clock=100.0;self.events=[];self.mode_commands=[]
        session=m.WatchdogPracticeSession(lambda *a:self.events.append(a),now=lambda:self.clock,transact=self.mode_commands.append)
        session.fd=123;session.watch_token=456
        return session

    def test_enable_requires_armed_brain_watchdog(self):
        session=self.session()
        with self.assertRaisesRegex(RuntimeError,'not armed'):session.run('AUTON')
        self.assertEqual(self.mode_commands,[])

    def test_matching_brain_ack_is_required_not_just_vex_ack(self):
        session=self.session()
        def now():self.clock+=0.025;return self.clock
        session.now=now
        with patch.object(m,'write_packet'),patch.object(m,'wait_for_reply',return_value=fifo_reply('')):
            with self.assertRaisesRegex(TimeoutError,'No matching Brain'):session.watch('WATCH_ARM')
        self.assertFalse(session.watch_armed)
        self.assertEqual(self.mode_commands,[])

    def test_wrong_nonce_ignored_and_split_brain_ack_accepted(self):
        session=self.session()
        replies=[fifo_reply('@RECF/1 1 999 OK STOP WATCHDOG 5 ARMED\n'),fifo_reply('@RECF/1 1 456 OK STOP '),fifo_reply('WATCHDOG 5 ARMED\n')]
        with patch.object(m,'write_packet') as write,patch.object(m,'wait_for_reply',side_effect=replies):
            session.watch('WATCH_ARM')
            frames=[call.args[1] for call in write.call_args_list]
            self.assertEqual(sum(b'WATCH_ARM' in frame for frame in frames),1)
        self.assertEqual(session.last_watch_ack,100)

    def test_expired_brain_reply_is_rejected(self):
        session=self.session()
        with patch.object(m,'write_packet'),patch.object(m,'wait_for_reply',return_value=fifo_reply('@RECF/1 1 456 ERR STOP WATCHDOG 4 EXPIRED\n')):
            with self.assertRaisesRegex(RuntimeError,'EXPIRED'):session.watch('WATCH_BEAT')
        self.assertEqual(self.mode_commands,[])

    def test_fresh_brain_heartbeat_precedes_native_enable(self):
        session=self.session();session.watch_armed=True
        order=[]
        session.watch=lambda cmd:order.append(cmd)
        session.transact=lambda packet:order.append(packet[7])
        session.run('AUTON')
        self.assertEqual(order,['WATCH_BEAT',10])

    def test_heartbeat_continues_while_disabled(self):
        session=self.session();session.watch_armed=True;session.next_beat=99
        calls=[];session.watch=calls.append
        session.tick()
        self.assertEqual(calls,['WATCH_BEAT'])
        self.assertFalse(session.enabled)

    def test_disconnect_latches_brain_stop_and_never_disarms_it(self):
        session=self.session();session.watch_armed=True;calls=[];session.watch=calls.append
        session.disconnect()
        self.assertEqual(calls,['WATCH_STOP'])
        self.assertEqual(self.mode_commands[-1][7],11)
        self.assertFalse(session.connected)
        self.assertFalse(session.watch_armed)

if __name__=='__main__':unittest.main()
