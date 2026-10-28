import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import unittest
spec=importlib.util.spec_from_file_location('windows_tester',Path(__file__).with_name('controller_serial_test.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class WindowsTransportTests(unittest.TestCase):
    def test_windows_transport_never_uses_posix_fd_io(self):
        writes=[]
        port=SimpleNamespace(in_waiting=4,write=lambda data:(writes.append(bytes(data)) or len(data)),read=lambda size:b'test')
        with patch.object(m,'IS_WINDOWS',True),patch.object(m.os,'write',side_effect=AssertionError('POSIX write')),patch.object(m.os,'read',side_effect=AssertionError('POSIX read')):
            self.assertTrue(m.readable(port,.1))
            m.write_packet(port,b'hello',lambda *a:None)
            self.assertEqual(writes,[b'hello'])
            self.assertEqual(m.read_chunk(port,lambda *a:None),b'test')
    def test_windows_probe_wait_has_a_deadline(self):
        with patch.object(m,'IS_WINDOWS',True):
            self.assertFalse(m.readable(SimpleNamespace(in_waiting=0),0))
