# the-registry

Record-keeping core for a new nation. Step 2 of the Nation Kit's 17-to-1
reverse-SDG build sequence.

## The idea

Every federal agency is one class with one job. This build centralizes the
three record-keeping classes:

- `PatentOffice` — one job: prove who invented what first. Append-only
  invention timestamp log with a tamper-evident hash chain, plus optional
  live USPTO corroboration.
- `Discloser` — one job: public companies publish true numbers. Disclosure
  registry that pulls live 10-K facts from SEC EDGAR, with a labeled cache
  fallback.
- `Census` — one job: count every person, know where they live. Population
  registry with household records, headcount and demographic summaries.
  Demo data is synthetic and labeled; real counts come through CSV import.

## SDGs unlocked

This build unlocks **SDG 16 (Peace, Justice and Strong Institutions)**.
Property rights need a record of who invented what. Markets need companies
to publish true numbers. A state that cannot count its people cannot serve
them. Records are the institutional half of the 17-to-1 sequence: the
ledger (step 1) made the money honest, the registry makes the claims
honest.

## Usage

```bash
# PatentOffice: timestamp a disclosure
python3 registry_cli.py patent record --title "Water valve" \
  --inventor "A. Maker" --description "A valve that passes water one way."
python3 registry_cli.py patent verify --id INV-000001
python3 registry_cli.py patent audit
python3 registry_cli.py patent first-claim --title "Water valve"
python3 registry_cli.py patent uspto-check --number 11234567

# Discloser: register a company, pull its live 10-K facts
python3 registry_cli.py disclose register --ticker AAPL --name "Apple Inc."
python3 registry_cli.py disclose pull --ticker AAPL
python3 registry_cli.py disclose latest --ticker AAPL

# Census: households, headcount, summaries
python3 registry_cli.py census household --id H-001 --locality Northfield \
  --members '{"0-17": 2, "35-54": 2}'
python3 registry_cli.py census seed --households 200
python3 registry_cli.py census headcount
python3 registry_cli.py census summary
python3 registry_cli.py census import --csv real_counts.csv
```

Data lives in `data/` (JSON). `--data-dir` overrides the location.

## Data sources and labels

- Patent timestamps: generated locally at record time (UTC ISO 8601). The
  hash chain is SHA-256 over canonical record JSON plus the previous hash.
- USPTO corroboration: live query to USPTO PPUBS (ppubs.uspto.gov),
  labeled with check date. Network failures return "unavailable", never a
  guess.
- Company disclosures: SEC EDGAR companyfacts (data.sec.gov), live-first
  with a descriptive User-Agent per SEC fair-access policy. Cached
  snapshots are labeled with their pull date.
- Census demo data: synthetic, deterministically generated, labeled
  "SYNTHETIC DEMO DATA" in every output. No real personal data is bundled.
  CSV import expects columns: household_id, locality, then one integer
  column per age band (0-17, 18-34, 35-54, 55-74, 75+).

## Reuse

- USPTO corroboration follows the plain-text search plus client-side
  filtering approach proven in mergers-and-acquisitions-for-peace; patent
  parsing conventions follow patent-portfolio-apis.
- The SEC EDGAR live-pull pattern (companyfacts, CIK zero-padding, latest
  10-K fact selection, live-first with labeled cache fallback) is vendored
  from sp500-corporate-stack/live_data.py.

## Honest limits

- The hash chain proves a record has not changed since it was written. It
  does not prove the invention works, is novel, or belongs to the
  claimant. It is defensive publication, not a patent grant.
- `first_claim` answers priority within this log only. Real priority
  disputes need the full patent record.
- Discloser stores what companies published. It does not audit whether the
  numbers are true.
- Census counts what was recorded or imported. It does not find people who
  were never recorded.

## TRL

TRL 8: complete system, qualified through test (25/25) and demonstrated
end-to-end on the CLI, released as v0.1.0. The gap to 9 is operational use:
a real nation recording real disclosures, filings, and counts.

## License

Apache-2.0.
