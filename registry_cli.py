#!/usr/bin/env python3
"""the-registry CLI: record-keeping core for a new nation.

Subcommands:
  patent record --title T --inventor I --description D [--kind K] [--ref-url U]
  patent verify --id INV-000001
  patent audit
  patent first-claim --title T
  patent uspto-check --number N        (live USPTO corroboration)
  disclose register --ticker T --name N [--cik C]
  disclose pull --ticker T [--refresh] (live SEC EDGAR, labeled cache fallback)
  disclose latest --ticker T
  census household --id H --locality L --members JSON
  census seed [--households N]
  census headcount
  census summary
  census import --csv PATH
  census clear

Global: --data-dir DIR (default: data/)
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from patent_office import PatentOffice
from discloser import Discloser
from census import Census, AGE_BANDS


def _paths(data_dir):
    return {
        "patents": os.path.join(data_dir, "patents.json"),
        "companies": os.path.join(data_dir, "companies.json"),
        "disclosures": os.path.join(data_dir, "disclosures"),
        "census": os.path.join(data_dir, "census.json"),
    }


def _usd(v):
    return "$%s" % f"{v:,.0f}" if isinstance(v, (int, float)) else "n/a"


def cmd_patent(args, p):
    po = PatentOffice(p["patents"])
    if args.action == "record":
        r = po.record_invention(args.title, args.inventor, args.description,
                                kind=args.kind, ref_url=args.ref_url or "")
        print("recorded %s at %s" % (r["id"], r["recorded_at"]))
        print("hash %s" % r["record_hash"][:16] + "...")
    elif args.action == "verify":
        ok, detail = po.verify(args.id)
        print(("VALID: " if ok else "INVALID: ") + detail)
    elif args.action == "audit":
        ok, n, detail = po.audit()
        print(("VALID: " if ok else "INVALID: ") + "%d records, %s" % (n, detail))
    elif args.action == "first-claim":
        r = po.first_claim(args.title)
        if r:
            print("first claim: %s by %s at %s" % (
                r["id"], r["inventor"], r["recorded_at"]))
        else:
            print("no claim recorded for that title")
    elif args.action == "uspto-check":
        r = po.uspto_check(args.number)
        print(json.dumps(r, indent=2))


def cmd_disclose(args, p):
    d = Discloser(p["companies"], p["disclosures"])
    if args.action == "register":
        c = d.register_company(args.ticker, args.name, cik=args.cik)
        print("registered %s (%s) cik=%s" % (
            c["ticker"], c["name"], c["cik"] or "unresolved"))
    elif args.action == "pull":
        doc = d.pull_disclosure(args.ticker, refresh=args.refresh)
        print("provenance: %s" % doc.get("provenance"))
        if doc.get("provenance") == "error":
            print("error: %s" % doc.get("detail"))
            return
        print("%s %s | source: %s | pulled: %s" % (
            doc["ticker"], doc["name"], doc["source"], doc["pulled_at"]))
        for tag, fact in doc.get("facts", {}).items():
            print("  %-45s %s (period %s)" % (
                tag, _usd(fact["value_usd"]), fact["period_end"]))
        if doc.get("detail"):
            print("note: %s" % doc["detail"])
    elif args.action == "latest":
        doc = d.latest(args.ticker)
        if not doc:
            print("no snapshot stored for %s" % args.ticker.upper())
            return
        print("provenance: %s" % doc.get("provenance"))
        for tag, fact in doc.get("facts", {}).items():
            print("  %-45s %s (period %s)" % (
                tag, _usd(fact["value_usd"]), fact["period_end"]))


def cmd_census(args, p):
    c = Census(p["census"])
    if args.action == "household":
        try:
            members = json.loads(args.members)
        except json.JSONDecodeError as e:
            print("bad --members JSON: %s" % e)
            return
        try:
            h = c.record_household(args.id, args.locality, members)
        except ValueError as e:
            print("error: %s" % e)
            return
        print("recorded %s: %d persons in %s" % (
            h["household_id"], h["persons"], h["locality"]))
    elif args.action == "seed":
        n = c.seed_demo(n_households=args.households)
        print("seeded %d synthetic demo households (labeled)" % n)
    elif args.action == "headcount":
        h = c.headcount()
        print("persons: %d | households: %d" % (h["persons"], h["households"]))
        print("source: %s" % h["source"])
    elif args.action == "summary":
        s = c.summary()
        print("by locality:")
        for loc, v in sorted(s["by_locality"].items()):
            print("  %-12s %6d households %8d persons" % (
                loc, v["households"], v["persons"]))
        print("by age band:")
        for b in AGE_BANDS:
            print("  %-6s %8d" % (b, s["by_age_band"][b]))
        print("source: %s" % s["source"])
    elif args.action == "import":
        try:
            n = c.import_csv(args.csv)
        except (ValueError, KeyError, FileNotFoundError) as e:
            print("error: %s" % e)
            return
        print("imported %d households from %s" % (n, args.csv))
    elif args.action == "clear":
        c.clear()
        print("census cleared")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="registry_cli.py",
                                 description="the-registry: record-keeping core")
    ap.add_argument("--data-dir", default="data")
    sub = ap.add_subparsers(dest="cmd", required=True)

    pp = sub.add_parser("patent")
    ppa = pp.add_subparsers(dest="action", required=True)
    r = ppa.add_parser("record")
    r.add_argument("--title", required=True)
    r.add_argument("--inventor", required=True)
    r.add_argument("--description", required=True)
    r.add_argument("--kind", default="invention")
    r.add_argument("--ref-url", default="")
    v = ppa.add_parser("verify")
    v.add_argument("--id", required=True)
    ppa.add_parser("audit")
    f = ppa.add_parser("first-claim")
    f.add_argument("--title", required=True)
    u = ppa.add_parser("uspto-check")
    u.add_argument("--number", required=True)

    dp = sub.add_parser("disclose")
    dpa = dp.add_subparsers(dest="action", required=True)
    reg = dpa.add_parser("register")
    reg.add_argument("--ticker", required=True)
    reg.add_argument("--name", required=True)
    reg.add_argument("--cik", default=None)
    pl = dpa.add_parser("pull")
    pl.add_argument("--ticker", required=True)
    pl.add_argument("--refresh", action="store_true")
    lt = dpa.add_parser("latest")
    lt.add_argument("--ticker", required=True)

    cp = sub.add_parser("census")
    cpa = cp.add_subparsers(dest="action", required=True)
    hh = cpa.add_parser("household")
    hh.add_argument("--id", required=True)
    hh.add_argument("--locality", required=True)
    hh.add_argument("--members", required=True,
                    help='JSON age-band counts, e.g. \'{"0-17": 2, "35-54": 2}\'')
    sd = cpa.add_parser("seed")
    sd.add_argument("--households", type=int, default=200)
    cpa.add_parser("headcount")
    cpa.add_parser("summary")
    im = cpa.add_parser("import")
    im.add_argument("--csv", required=True)
    cpa.add_parser("clear")

    args = ap.parse_args(argv)
    paths = _paths(args.data_dir)
    if args.cmd == "patent":
        cmd_patent(args, paths)
    elif args.cmd == "disclose":
        cmd_disclose(args, paths)
    elif args.cmd == "census":
        cmd_census(args, paths)


if __name__ == "__main__":
    main()
