import importlib.util
from pathlib import Path
from unittest.mock import patch
import unittest
spec=importlib.util.spec_from_file_location('identity_tester',Path(__file__).with_name('controller_serial_test.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
from test_watchdog_sender import fifo_reply
class IdentityTests(unittest.TestCase):
    def session(self):
        self.sent=[]
        s=m.WatchdogPracticeSession(lambda *a:None,now=lambda:100.,transact=self.sent.append)
        s.fd=123;s.watch_token=456
        return s
    def test_matching_identity_nonce_and_sequence_are_required(self):
        s=self.session()
        replies=[fifo_reply('@RECF/1 1 999 ID '+m.EXPECTED_KERNEL+'\n'),fifo_reply('@RECF/1 1 456 ID '+m.EXPECTED_KERNEL+'\n')]
        with patch.object(m,'write_packet'),patch.object(m,'wait_for_reply',side_effect=replies):s.watch('WATCH_ID')
        self.assertEqual(s.kernel_identity,m.EXPECTED_KERNEL)
        self.assertFalse(s.watch_armed);self.assertEqual(s.last_watch_ack,0)
        self.assertEqual(self.sent,[])
    def test_wrong_family_version_build_or_capabilities_cannot_arm(self):
        for descriptor in ['STOCK 4.2.2','RECF_CONTROL_STATE 4.2.2 1.3.0 wrong 0000000f',m.EXPECTED_KERNEL.replace('0000000f','00000003')]:
            s=self.session()
            with patch.object(m,'write_packet'),patch.object(m,'wait_for_reply',return_value=fifo_reply('@RECF/1 1 456 ID '+descriptor+'\n')):
                with self.assertRaisesRegex(RuntimeError,'identity mismatch'):s.watch('WATCH_ID')
            self.assertFalse(s.watch_armed);self.assertIsNone(s.kernel_identity);self.assertEqual(self.sent,[])
    def test_connect_checks_identity_before_arming_and_never_falls_back(self):
        s=self.session();commands=[]
        def reject(command):
            commands.append(command)
            if command=='WATCH_ID':raise RuntimeError('identity mismatch')
        with patch.object(m.PracticeSession,'connect'),patch.object(s,'watch',side_effect=reject),patch.object(s,'failed'):
            with self.assertRaisesRegex(RuntimeError,'identity mismatch'):s.connect('/fake')
        self.assertEqual(commands,['WATCH_ID']);self.assertFalse(s.watch_armed)
    def test_connect_orders_identity_then_arm(self):
        s=self.session();commands=[]
        with patch.object(m.PracticeSession,'connect'),patch.object(s,'watch',side_effect=commands.append):s.connect('/fake')
        self.assertEqual(commands,['WATCH_ID','WATCH_ARM']);self.assertTrue(s.watch_armed)
