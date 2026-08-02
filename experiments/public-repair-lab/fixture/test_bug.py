#!/usr/bin/env python3
import tempfile
import unittest
from pathlib import Path

from buggy_writer import get_write_function


class PathOutputTest(unittest.TestCase):
    def test_path_output_appends_text(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "trace.log"
            writer = get_write_function(output)
            writer("first\n")
            writer("second\n")
            self.assertEqual(output.read_text(encoding="utf-8"), "first\nsecond\n")


if __name__ == "__main__":
    unittest.main()
