"""Offline smoke tests for the documented package interface."""

import subprocess
import sys
import unittest


class ImportTests(unittest.TestCase):
    def test_documented_import_preserves_existing_class_without_network(self):
        result = subprocess.run(
            [sys.executable, "-c", """
import sys

def deny_network(event, args):
    if event.startswith('socket.'):
        raise AssertionError('Network operation during import: ' + event)

sys.addaudithook(deny_network)
from pycarlink import PyCarlink
from pycarlink.PyCarLink import PyCarlink as ExistingClass
assert PyCarlink is ExistingClass
assert isinstance(PyCarlink, type)
"""],
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
