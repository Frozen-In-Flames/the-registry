"""PatentOffice: prove who invented what first.

One job: when two parties claim the same invention, the record shows who
was first. An append-only invention log with a tamper-evident hash chain:
each record commits to its own contents plus the hash of the record before
it, so altering any record breaks every record after it.

This is the defensive-publication half of a patent office. It does not
grant patents, examine claims, or replace the USPTO. It answers one
question: what was disclosed, by whom, and when. The optional
uspto_check() corroborates a filing against the live USPTO database.

Reuse note: the live USPTO corroboration follows the plain-text search
plus client-side filtering approach proven in mergers-and-acquisitions-
for-peace (the PPUBS BRS assignee syntax is unreliable). Patent parsing
conventions follow patent-portfolio-apis.
"""

import datetime
import hashlib
import json
import os
import urllib.parse
import urllib.request

USPTO_PPUBS = "https://ppubs.uspto.gov/pubwebapp/api/v1/search"
USER_AGENT = ("FrozenInFlames the-registry "
              "research contact@example.com")


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _canonical(record):
    """Canonical JSON of a record, excluding its own hash fields."""
    core = {k: v for k, v in record.items()
            if k not in ("record_hash", "prev_hash")}
    return json.dumps(core, sort_keys=True, separators=(",", ":"))


def _hash_record(record, prev_hash):
    payload = _canonical(record) + "|" + prev_hash
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class PatentOffice:
    GENESIS_HASH = "0" * 64

    def __init__(self, path):
        self.path = path
        self.records = []
        self._load()

    # -- persistence ---------------------------------------------------
    def _load(self):
        if os.path.exists(self.path):
            with open(self.path) as f:
                doc = json.load(f)
            self.records = doc.get("records", [])

    def _save(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.path)),
                    exist_ok=True)
        with open(self.path, "w") as f:
            json.dump({"records": self.records,
                       "exported_at": _now()}, f, indent=2)

    # -- the one job ----------------------------------------------------
    def record_invention(self, title, inventor, description,
                         kind="invention", ref_url=""):
        """Timestamp a disclosure. Returns the stored record."""
        prev_hash = (self.records[-1]["record_hash"]
                     if self.records else self.GENESIS_HASH)
        record = {
            "id": "INV-%06d" % (len(self.records) + 1),
            "title": title,
            "inventor": inventor,
            "description": description,
            "kind": kind,
            "ref_url": ref_url,
            "recorded_at": _now(),
            "prev_hash": prev_hash,
        }
        record["record_hash"] = _hash_record(record, prev_hash)
        self.records.append(record)
        self._save()
        return record

    def get(self, record_id):
        for r in self.records:
            if r["id"] == record_id:
                return r
        return None

    def verify(self, record_id):
        """Recompute the chain up to and including record_id.

        Returns (ok, detail). ok is True only if every hash from genesis
        to the record recomputes correctly.
        """
        target = self.get(record_id)
        if target is None:
            return False, "no such record"
        prev = self.GENESIS_HASH
        for r in self.records:
            want = _hash_record(r, prev)
            if r["record_hash"] != want:
                return False, "chain broken at %s" % r["id"]
            if r["prev_hash"] != prev:
                return False, "link broken at %s" % r["id"]
            prev = r["record_hash"]
            if r["id"] == record_id:
                break
        return True, "chain valid through %s" % record_id

    def audit(self):
        """Verify the whole chain. Returns (ok, checked, detail)."""
        if not self.records:
            return True, 0, "log empty"
        ok, detail = self.verify(self.records[-1]["id"])
        return ok, len(self.records), detail

    def first_claim(self, title):
        """Earliest record whose title matches (case-insensitive).

        This is the priority answer: who claimed it first.
        """
        needle = title.strip().lower()
        for r in self.records:
            if r["title"].strip().lower() == needle:
                return r
        return None

    def list(self):
        return list(self.records)

    # -- live corroboration (optional, network) -------------------------
    def uspto_check(self, patent_number, timeout=30):
        """Corroborate a US patent number against the live USPTO.

        Returns a dict with status "found" (plus filing/publication
        dates from the USPTO) or "unavailable"/"not_found". Network
        failures never raise; they are labeled.
        """
        number = "".join(ch for ch in patent_number if ch.isdigit())
        if not number:
            return {"status": "invalid_number",
                    "patent_number": patent_number}
        body = json.dumps({
            "query": "PN/%s" % number,
            "start": 0,
            "rows": 5,
        }).encode("utf-8")
        req = urllib.request.Request(
            USPTO_PPUBS, data=body,
            headers={"User-Agent": USER_AGENT,
                     "Content-Type": "application/json",
                     "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                doc = json.loads(r.read().decode("utf-8"))
        except Exception as e:
            return {"status": "unavailable",
                    "patent_number": patent_number,
                    "detail": "USPTO unreachable: %s" % str(e)[:120],
                    "checked_at": _now()}
        hits = (doc.get("results") or doc.get("docs") or [])
        if not hits:
            return {"status": "not_found", "patent_number": patent_number,
                    "checked_at": _now()}
        hit = hits[0]
        return {
            "status": "found",
            "patent_number": patent_number,
            "title": hit.get("inventionTitle") or hit.get("title", ""),
            "filing_date": hit.get("filingDate") or hit.get("appFilingDate", ""),
            "publication_date": hit.get("publicationDate", ""),
            "assignee": hit.get("assigneeName") or hit.get("assignee", ""),
            "source": "USPTO PPUBS (ppubs.uspto.gov)",
            "checked_at": _now(),
        }
