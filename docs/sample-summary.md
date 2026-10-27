# Cyber risk summary: Sample Co (fictional online lender)

Assessment date 2026-10-27.

Across 10 risks, the expected annual loss is $1.19M. In a 1-in-10 bad year, losses would exceed $2.94M. The 6 modelled treatments reduce expected annual loss to $520K, avoiding about $671K a year for $235K a year in cost (2.9x return). 4 risk(s) are above appetite: R-01, R-04, R-06, R-03. The largest exposure is R-01, ransomware encrypts core lending platform, at $277K expected per year.

## Decisions needed

1. Approve the mitigate plan for R-01 ($60K a year, owner Head of Infrastructure, due 2027-02-28).
2. Approve the mitigate plan for R-04 ($40K a year, owner Vulnerability Management, due 2026-12-31).
3. Approve the transfer plan for R-06 ($45K a year, owner Chief Risk Officer, due 2027-03-31).
4. Approve the mitigate plan for R-03 ($30K a year, owner Cloud Platform team, due 2027-01-31).
5. Re-examine the treatment for R-10: it avoids about $44K a year for $35K, a return of only 0.25 per dollar.
6. R-06 was due for review on 2026-10-01 (Chief Risk Officer).

## Risks by expected annual loss

| ID | Risk | Residual | Expected loss / year | 1-in-10 year | Chance of any loss | Appetite |
|---|---|---|---|---|---|---|
| R-01 | Ransomware encrypts core lending platform | 10 (medium) | $277K | $922K | 11% | **Above** |
| R-04 | Exploitation of an unpatched internet-facing vulnerability | 12 (high) | $194K | $770K | 29% | **Above** |
| R-06 | Breach at a third-party loan servicing vendor | 12 (high) | $180K | $818K | 17% | **Above** |
| R-03 | Customer data exposed through misconfigured cloud storage | 10 (medium) | $168K | $427K | 11% | **Above** |
| R-02 | Business email compromise leads to fraudulent wire payment | 9 (medium) | $117K | $403K | 39% | Within |
| R-05 | Broken access control in customer API exposes other customers' loans | 8 (medium) | $94K | $326K | 12% | Within |
| R-10 | Credential stuffing takes over customer accounts | 9 (medium) | $58K | $125K | 86% | Within |
| R-07 | Insider copies customer data before leaving | 6 (medium) | $55K | $247K | 20% | Within |
| R-08 | DDoS attack takes the loan application site offline | 4 (low) | $34K | $107K | 44% | Within |
| R-09 | Lost or stolen laptop with customer data | 3 (low) | $13K | $25K | 94% | Within |

Simulated with 10,000 years per risk (seed 27001). Estimates are calibrated ranges, so results are directional and should be read as orders of magnitude.
