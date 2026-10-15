import json
import os
import subprocess
import sys
import tempfile
import unittest

CLI = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "registry_cli.py")


def run(data_dir, *args):
    return subprocess.run(
        [sys.executable, CLI, "--data-dir", data_dir] + list(args),
        capture_output=True, text=True, timeout=60)


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_patent_flow(self):
        r = run(self.tmp, "patent", "record", "--title", "Test valve",
                "--inventor", "A. Maker", "--description", "A test valve.")
        self.assertIn("recorded INV-000001", r.stdout)
        r = run(self.tmp, "patent", "verify", "--id", "INV-000001")
        self.assertIn("VALID", r.stdout)
        r = run(self.tmp, "patent", "audit")
        self.assertIn("1 records", r.stdout)
        r = run(self.tmp, "patent", "first-claim", "--title", "test valve")
        self.assertIn("A. Maker", r.stdout)

    def test_disclose_register_and_latest_empty(self):
        r = run(self.tmp, "disclose", "register", "--ticker", "ACME",
                "--name", "Acme Corp", "--cik", "1234")
        self.assertIn("registered ACME", r.stdout)
        r = run(self.tmp, "disclose", "latest", "--ticker", "ACME")
        self.assertIn("no snapshot", r.stdout)

    def test_census_flow(self):
        r = run(self.tmp, "census", "household", "--id", "H-1",
                "--locality", "Northfield",
                "--members", '{"0-17": 2, "35-54": 2}')
        self.assertIn("4 persons", r.stdout)
        r = run(self.tmp, "census", "headcount")
        self.assertIn("persons: 4", r.stdout)
        r = run(self.tmp, "census", "summary")
        self.assertIn("Northfield", r.stdout)
        r = run(self.tmp, "census", "seed", "--households", "25")
        self.assertIn("25 synthetic", r.stdout)
