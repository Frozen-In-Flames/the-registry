import csv
import os
import tempfile
import unittest

from census import Census, AGE_BANDS, DEMO_LABEL


class TestCensus(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.c = Census(os.path.join(self.tmp, "census.json"))

    def test_record_and_headcount(self):
        self.c.record_household("H-1", "Northfield",
                               {"0-17": 2, "35-54": 2})
        self.c.record_household("H-2", "Eastvale", {"18-34": 1})
        h = self.c.headcount()
        self.assertEqual(h["persons"], 5)
        self.assertEqual(h["households"], 2)

    def test_unknown_band_rejected(self):
        with self.assertRaises(ValueError):
            self.c.record_household("H-1", "X", {"0-99": 1})

    def test_negative_count_rejected(self):
        with self.assertRaises(ValueError):
            self.c.record_household("H-1", "X", {"0-17": -1})

    def test_summary(self):
        self.c.record_household("H-1", "Northfield",
                               {"0-17": 2, "35-54": 1})
        s = self.c.summary()
        self.assertEqual(s["by_locality"]["Northfield"]["persons"], 3)
        self.assertEqual(s["by_age_band"]["0-17"], 2)
        self.assertEqual(s["by_age_band"]["75+"], 0)

    def test_seed_demo_labeled(self):
        n = self.c.seed_demo(n_households=50, seed=1)
        self.assertEqual(n, 50)
        h = self.c.headcount()
        self.assertEqual(h["households"], 50)
        self.assertGreater(h["persons"], 0)
        self.assertIn("SYNTHETIC", h["source"])

    def test_import_csv(self):
        p = os.path.join(self.tmp, "real.csv")
        with open(p, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["household_id", "locality"] + AGE_BANDS)
            w.writerow(["R-1", "Westport", 1, 0, 2, 0, 0])
            w.writerow(["R-2", "Westport", 0, 1, 1, 0, 0])
        n = self.c.import_csv(p)
        self.assertEqual(n, 2)
        h = self.c.headcount()
        self.assertEqual(h["persons"], 5)
        self.assertIn("real.csv", h["source"])

    def test_clear(self):
        self.c.seed_demo(n_households=10)
        self.c.clear()
        h = self.c.headcount()
        self.assertEqual(h["persons"], 0)
        self.assertEqual(h["households"], 0)

    def test_persistence(self):
        self.c.record_household("H-1", "Northfield", {"0-17": 1})
        c2 = Census(os.path.join(self.tmp, "census.json"))
        self.assertEqual(c2.headcount()["persons"], 1)
