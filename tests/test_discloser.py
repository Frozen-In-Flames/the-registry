import json
import os
import tempfile
import unittest
from unittest import mock

import discloser
from discloser import Discloser, _latest_10k_fact


SAMPLE_FACTS = {
    "facts": {
        "us-gaap": {
            "Assets": {"units": {"USD": [
                {"val": 1000, "end": "2024-12-31", "form": "10-K",
                 "fp": "FY", "filed": "2025-02-01"},
                {"val": 1200, "end": "2025-12-31", "form": "10-K",
                 "fp": "FY", "filed": "2026-02-01"},
            ]}},
            "Revenues": {"units": {"USD": [
                {"val": 500, "end": "2025-12-31", "form": "10-K",
                 "fp": "FY", "filed": "2026-02-01"},
            ]}},
        }
    }
}


class TestDiscloser(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.d = Discloser(os.path.join(self.tmp, "companies.json"),
                           os.path.join(self.tmp, "disclosures"))

    def test_register(self):
        c = self.d.register_company("acme", "Acme Corp", cik="1234")
        self.assertEqual(c["ticker"], "ACME")
        self.assertEqual(c["cik"], "0000001234")

    def test_latest_10k_fact_picks_latest(self):
        units = SAMPLE_FACTS["facts"]["us-gaap"]["Assets"]["units"]["USD"]
        val, end = _latest_10k_fact(units)
        self.assertEqual(val, 1200.0)
        self.assertEqual(end, "2025-12-31")

    def test_pull_live(self):
        self.d.register_company("ACME", "Acme Corp", cik="1234")
        with mock.patch.object(discloser, "_sec_get_json",
                               return_value=SAMPLE_FACTS):
            doc = self.d.pull_disclosure("ACME")
        self.assertEqual(doc["provenance"], "live")
        self.assertEqual(doc["facts"]["Assets"]["value_usd"], 1200.0)
        self.assertEqual(doc["facts"]["Revenues"]["value_usd"], 500.0)
        self.assertIn("SEC EDGAR", doc["source"])

    def test_pull_falls_back_to_cache(self):
        self.d.register_company("ACME", "Acme Corp", cik="1234")
        with mock.patch.object(discloser, "_sec_get_json",
                               return_value=SAMPLE_FACTS):
            self.d.pull_disclosure("ACME")
        with mock.patch.object(discloser, "_sec_get_json",
                               side_effect=ConnectionError("down")):
            doc = self.d.pull_disclosure("ACME")
        self.assertTrue(doc["provenance"].startswith("cached:"))
        self.assertIn("cached", doc["detail"])

    def test_pull_no_cache_no_network_errors_honestly(self):
        self.d.register_company("ACME", "Acme Corp", cik="1234")
        with mock.patch.object(discloser, "_sec_get_json",
                               side_effect=ConnectionError("down")):
            doc = self.d.pull_disclosure("ACME")
        self.assertEqual(doc["provenance"], "error")
        self.assertIn("no cache", doc["detail"])

    def test_pull_unregistered(self):
        doc = self.d.pull_disclosure("NOPE")
        self.assertEqual(doc["provenance"], "error")

    def test_latest_none(self):
        self.assertIsNone(self.d.latest("ACME"))
