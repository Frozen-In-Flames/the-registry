"""Discloser: public companies publish true numbers.

One job: a public company must publish its financials, and the registry
must hold what was published, when, and from where. This is the disclosure
half of securities regulation: it does not judge whether the numbers are
true, it makes the published numbers retrievable and timestamped.

Live-first: pull_disclosure() queries SEC EDGAR companyfacts at runtime.
If the network is unreachable and a cached snapshot exists, the cached
snapshot is returned, always labeled with its pull date. --refresh forces
a fresh pull.

Reuse note: the companyfacts pull pattern (descriptive User-Agent per SEC
fair-access policy, CIK zero-padded URLs, latest 10-K fact selection) is
vendored from sp500-corporate-stack/live_data.py.
"""

import datetime
import json
import os
import urllib.request

SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK%010d.json"
USER_AGENT = ("FrozenInFlames the-registry "
              "research contact@example.com")

# Facts worth keeping from a 10-K. us-gaap tags; missing tags are skipped,
# never invented.
TRACKED_FACTS = [
    "Assets",
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "NetIncomeLoss",
    "Liabilities",
    "StockholdersEquity",
    "CashAndCashEquivalentsAtCarryingValue",
    "LongTermDebt",
]


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _sec_get_json(url, timeout=60):
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _latest_10k_fact(units):
    """Latest-filed 10-K fact across FY rows. Returns (value, end) or None."""
    tens = [u for u in (units or [])
            if u.get("form") == "10-K" and u.get("end")]
    if not tens:
        return None
    tens.sort(key=lambda u: (u["end"], str(u.get("filed", ""))))
    latest = tens[-1]
    try:
        return float(latest["val"]), latest["end"]
    except (TypeError, ValueError):
        return None


class Discloser:
    def __init__(self, registry_path, cache_dir):
        self.registry_path = registry_path
        self.cache_dir = cache_dir
        self.companies = {}
        self._load()

    # -- persistence ---------------------------------------------------
    def _load(self):
        if os.path.exists(self.registry_path):
            with open(self.registry_path) as f:
                self.companies = json.load(f).get("companies", {})

    def _save(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.registry_path)),
                    exist_ok=True)
        with open(self.registry_path, "w") as f:
            json.dump({"companies": self.companies,
                       "exported_at": _now()}, f, indent=2)

    def _cache_path(self, ticker):
        os.makedirs(self.cache_dir, exist_ok=True)
        return os.path.join(self.cache_dir, "%s.json" % ticker.upper())

    # -- the one job ----------------------------------------------------
    def register_company(self, ticker, name, cik=None):
        """Add a company to the disclosure registry."""
        t = ticker.upper()
        self.companies[t] = {"ticker": t, "name": name,
                             "cik": str(cik).zfill(10) if cik else None,
                             "registered_at": _now()}
        self._save()
        return self.companies[t]

    def resolve_cik(self, ticker):
        """Resolve a ticker to a CIK via the SEC ticker map (network)."""
        t = ticker.upper()
        known = (self.companies.get(t) or {}).get("cik")
        if known:
            return known
        doc = _sec_get_json(SEC_TICKERS_URL)
        for v in doc.values():
            if str(v.get("ticker", "")).upper() == t:
                cik = str(v["cik_str"]).zfill(10)
                if t in self.companies:
                    self.companies[t]["cik"] = cik
                    self._save()
                return cik
        raise ValueError("ticker %s not found in SEC ticker map" % t)

    def pull_disclosure(self, ticker, refresh=False):
        """Pull the latest 10-K facts for a company, live-first.

        Returns {"provenance": "live"|"cached:DATE"|"error", ...}.
        """
        t = ticker.upper()
        co = self.companies.get(t)
        if co is None:
            return {"provenance": "error", "ticker": t,
                    "detail": "company not registered"}

        def read_cache():
            p = self._cache_path(t)
            if os.path.exists(p):
                with open(p) as f:
                    return json.load(f)
            return None

        # Live-first: the network is always tried first. `refresh` exists
        # for CLI parity with the other Nation Kit builds; here it changes
        # nothing because live is the default path.
        try:
            cik = co.get("cik") or self.resolve_cik(t)
            facts = _sec_get_json(SEC_FACTS_URL % int(cik))
            usgaap = facts.get("facts", {}).get("us-gaap", {})
            snapshot = {}
            for tag in TRACKED_FACTS:
                units = usgaap.get(tag, {}).get("units", {}).get("USD", [])
                got = _latest_10k_fact(units)
                if got:
                    snapshot[tag] = {"value_usd": got[0],
                                    "period_end": got[1]}
            doc = {"ticker": t, "name": co["name"], "cik": cik,
                   "source": "SEC EDGAR companyfacts (data.sec.gov)",
                   "pulled_at": _now(), "facts": snapshot}
            with open(self._cache_path(t), "w") as f:
                json.dump(doc, f, indent=2)
            doc["provenance"] = "live"
            return doc
        except Exception as e:
            cached = read_cache()
            if cached is not None:
                cached["provenance"] = ("cached:%s"
                                        % cached.get("pulled_at",
                                                     "unknown date"))
                cached["detail"] = ("live pull failed (%s); showing cached "
                                    "snapshot" % str(e)[:120])
                return cached
            return {"provenance": "error", "ticker": t,
                    "detail": "live pull failed and no cache exists: %s"
                    % str(e)[:160]}

    def latest(self, ticker):
        """Newest stored snapshot regardless of provenance."""
        p = self._cache_path(ticker.upper())
        if os.path.exists(p):
            with open(p) as f:
                doc = json.load(f)
            doc.setdefault("provenance",
                           "cached:%s" % doc.get("pulled_at", "unknown"))
            return doc
        return None

    def registered(self):
        return dict(self.companies)
