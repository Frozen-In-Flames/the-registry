"""patent-portfolio-apis wiring: used when present, fallback offline."""
import os, sys, types, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import uspto_source
from patent_office import PatentOffice

class FakeClient:
    def __init__(self, *a, **k): pass
    def fetch_patent(self, number):
        return {"inventionTitle": "Fake Title", "filingDate": "2020-01-01",
                "publicationDate": "2021-01-01", "assigneeName": "Fake Co"}
    def close(self): pass

def fake_uspto_module():
    m = types.ModuleType("ppa.uspto"); m.PPUBSClient = FakeClient
    pkg = types.ModuleType("ppa"); pkg.uspto = m
    return pkg, m

class TestUsptoSource(unittest.TestCase):
    def setUp(self):
        self._saved = {k: sys.modules.get(k) for k in ("ppa", "ppa.uspto")}
    def tearDown(self):
        for k, v in self._saved.items():
            if v is None: sys.modules.pop(k, None)
            else: sys.modules[k] = v
    def test_ppa_client_is_used_when_importable(self):
        pkg, m = fake_uspto_module()
        sys.modules["ppa"] = pkg; sys.modules["ppa.uspto"] = m
        self.assertTrue(uspto_source.available())
        out = uspto_source.fetch_patent("1234567")
        self.assertEqual(out["status"], "found")
        self.assertEqual(out["source"], "patent-portfolio-apis (USPTO PPUBS)")
        self.assertEqual(out["title"], "Fake Title")
    def test_office_check_prefers_ppa_and_labels_source(self):
        pkg, m = fake_uspto_module()
        sys.modules["ppa"] = pkg; sys.modules["ppa.uspto"] = m
        import tempfile
        po = PatentOffice(os.path.join(tempfile.mkdtemp(), "patents.json"))
        out = po.uspto_check("US1234567")
        self.assertEqual(out["status"], "found")
        self.assertIn("patent-portfolio-apis", out["source"])
    def test_offline_fallback_never_raises(self):
        # No network in the test environment is required: the direct
        # fallback labels failure instead of raising, and an invalid
        # number is rejected before any network use.
        import tempfile
        po = PatentOffice(os.path.join(tempfile.mkdtemp(), "patents.json"))
        self.assertEqual(po.uspto_check("not-a-number")["status"], "invalid_number")
        out = po._uspto_check_direct("1234567", timeout=1)
        self.assertIn(out["status"], ("found", "not_found", "unavailable"))
if __name__ == "__main__": unittest.main()
