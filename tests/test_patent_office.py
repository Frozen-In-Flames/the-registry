import json
import os
import tempfile
import unittest

from patent_office import PatentOffice, _hash_record


class TestPatentOffice(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.po = PatentOffice(os.path.join(self.tmp, "patents.json"))

    def test_record_and_chain(self):
        r1 = self.po.record_invention("Water valve", "A. Inventor",
                                      "A valve that passes water one way.")
        r2 = self.po.record_invention("Solar lens", "B. Maker",
                                      "A lens that focuses sunlight.")
        self.assertEqual(r1["id"], "INV-000001")
        self.assertEqual(r2["prev_hash"], r1["record_hash"])
        ok, n, detail = self.po.audit()
        self.assertTrue(ok)
        self.assertEqual(n, 2)

    def test_verify_single(self):
        r = self.po.record_invention("X", "Y", "Z")
        ok, detail = self.po.verify(r["id"])
        self.assertTrue(ok)

    def test_tamper_detected(self):
        r = self.po.record_invention("X", "Y", "Z")
        self.po.record_invention("A", "B", "C")
        self.po.records[0]["title"] = "TAMPERED"
        ok, detail = self.po.verify(r["id"])
        self.assertFalse(ok)
        self.assertIn("broken", detail)

    def test_first_claim_priority(self):
        self.po.record_invention("Widget", "Second", "later claim")
        first = self.po.first_claim("widget")
        self.assertEqual(first["inventor"], "Second")
        self.assertEqual(first["id"], "INV-000001")
        self.po.record_invention("Widget", "Third", "even later claim")
        first = self.po.first_claim("WIDGET")
        self.assertEqual(first["id"], "INV-000001")
        self.assertIsNone(self.po.first_claim("nonexistent thing"))

    def test_persistence(self):
        self.po.record_invention("X", "Y", "Z")
        po2 = PatentOffice(os.path.join(self.tmp, "patents.json"))
        ok, n, _ = po2.audit()
        self.assertTrue(ok)
        self.assertEqual(n, 1)

    def test_empty_audit(self):
        ok, n, detail = self.po.audit()
        self.assertTrue(ok)
        self.assertEqual(n, 0)

    def test_uspto_check_invalid_number(self):
        r = self.po.uspto_check("not-a-number")
        self.assertEqual(r["status"], "invalid_number")
