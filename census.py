"""Census: count every person, know where they live.

One job: the nation knows how many people it has and where they are.
Household records with locality and age-band counts. No names, no real
personal data: the built-in demo data is synthetic and labeled as such.
Real counts arrive through import_csv(), which reads a documented column
format (locality, households, age bands).

What this deliberately does not do: identity anyone. Age bands, not ages;
localities, not addresses.
"""

import csv
import datetime
import json
import os
import random

AGE_BANDS = ["0-17", "18-34", "35-54", "55-74", "75+"]

DEMO_LABEL = ("SYNTHETIC DEMO DATA: generated locally for demonstration, "
              "not real people")


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class Census:
    def __init__(self, path):
        self.path = path
        self.households = {}
        self.meta = {}
        self._load()

    # -- persistence ---------------------------------------------------
    def _load(self):
        if os.path.exists(self.path):
            with open(self.path) as f:
                doc = json.load(f)
            self.households = doc.get("households", {})
            self.meta = doc.get("meta", {})

    def _save(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.path)),
                    exist_ok=True)
        with open(self.path, "w") as f:
            json.dump({"households": self.households, "meta": self.meta,
                       "exported_at": _now()}, f, indent=2)

    # -- the one job ----------------------------------------------------
    def record_household(self, household_id, locality, members,
                         source="manual"):
        """Record one household.

        members: dict of age_band -> count, e.g. {"0-17": 2, "35-54": 2}.
        Unknown bands raise ValueError; they are not silently dropped.
        """
        bad = [b for b in members if b not in AGE_BANDS]
        if bad:
            raise ValueError("unknown age bands: %s (use %s)"
                             % (bad, AGE_BANDS))
        for band, n in members.items():
            if not isinstance(n, int) or n < 0:
                raise ValueError("member counts must be non-negative ints")
        self.households[household_id] = {
            "household_id": household_id,
            "locality": locality,
            "members": {b: members.get(b, 0) for b in AGE_BANDS},
            "persons": sum(members.values()),
            "source": source,
            "recorded_at": _now(),
        }
        self.meta["updated_at"] = _now()
        self._save()
        return self.households[household_id]

    def headcount(self):
        """Total persons and households, with data source label."""
        persons = sum(h["persons"] for h in self.households.values())
        return {"persons": persons,
                "households": len(self.households),
                "source": self.meta.get("source_label", "manual records"),
                "as_of": self.meta.get("updated_at")}

    def summary(self):
        """Breakdown by locality and by age band."""
        by_locality = {}
        by_band = {b: 0 for b in AGE_BANDS}
        for h in self.households.values():
            loc = h["locality"]
            by_locality.setdefault(loc, {"households": 0, "persons": 0})
            by_locality[loc]["households"] += 1
            by_locality[loc]["persons"] += h["persons"]
            for b in AGE_BANDS:
                by_band[b] += h["members"][b]
        return {"by_locality": by_locality, "by_age_band": by_band,
                "source": self.meta.get("source_label", "manual records")}

    def import_csv(self, csv_path, locality_col="locality",
                   household_col="household_id"):
        """Import real counts. Columns: household_id, locality, then one
        column per age band in AGE_BANDS holding integer counts."""
        imported = 0
        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                members = {}
                for b in AGE_BANDS:
                    raw = (row.get(b) or "0").strip()
                    members[b] = int(raw) if raw else 0
                self.record_household(
                    row[household_col], row[locality_col], members,
                    source="csv:%s" % os.path.basename(csv_path))
                imported += 1
        self.meta["source_label"] = "imported CSV: %s (%d households)" % (
            os.path.basename(csv_path), imported)
        self._save()
        return imported

    def seed_demo(self, n_households=200, seed=42):
        """Generate deterministic synthetic households, clearly labeled."""
        rng = random.Random(seed)
        localities = ["Northfield", "Eastvale", "Westport", "Southgate"]
        self.households = {}
        for i in range(n_households):
            members = {}
            size = rng.choice([1, 2, 2, 3, 3, 4, 4, 5])
            remaining = size
            bands = rng.sample(AGE_BANDS, k=rng.randint(1, 3))
            for j, b in enumerate(bands):
                n = remaining if j == len(bands) - 1 else rng.randint(
                    0, remaining)
                members[b] = n
                remaining -= n
            self.record_household("DEMO-%05d" % (i + 1),
                                  rng.choice(localities), members,
                                  source="synthetic-demo")
        self.meta["source_label"] = DEMO_LABEL
        self._save()
        return n_households

    def clear(self):
        self.households = {}
        self.meta = {}
        self._save()
