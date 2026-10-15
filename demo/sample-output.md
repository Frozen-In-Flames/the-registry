$ python3 registry_cli.py patent record --title "Phase-cycle water valve" --inventor "A. Maker" --description "..."
recorded INV-000001 at 2026-10-15T19:57:18.491185+00:00
hash 778b20a62a45eed4...
$ python3 registry_cli.py patent audit
VALID: 1 records, chain valid through INV-000001
$ python3 registry_cli.py census seed --households 200 && python3 registry_cli.py census headcount
seeded 200 synthetic demo households (labeled)
persons: 596 | households: 200
source: SYNTHETIC DEMO DATA: generated locally for demonstration, not real people
$ python3 registry_cli.py disclose register --ticker MSFT --name "Microsoft Corp" && python3 registry_cli.py disclose pull --ticker MSFT
registered MSFT (Microsoft Corp) cik=unresolved
provenance: live
MSFT Microsoft Corp | source: SEC EDGAR companyfacts (data.sec.gov) | pulled: 2026-10-15T19:57:22.874381+00:00
  Assets                                        $758,376,000,000 (period 2026-06-30)
  Revenues                                      $16,039,000,000 (period 2010-06-30)
  RevenueFromContractWithCustomerExcludingAssessedTax $331,839,000,000 (period 2026-06-30)
  NetIncomeLoss                                 $133,749,000,000 (period 2026-06-30)
  Liabilities                                   $315,989,000,000 (period 2026-06-30)
  StockholdersEquity                            $442,387,000,000 (period 2026-06-30)
  CashAndCashEquivalentsAtCarryingValue         $20,935,000,000 (period 2026-06-30)
  LongTermDebt                                  $40,294,000,000 (period 2026-06-30)
