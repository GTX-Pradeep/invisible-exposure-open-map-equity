# Internal research audit (2026-11-11)

A methodological review of the manuscript, done before the journal revision. It lists each issue we found, what we did about it, and where the evidence is. All numbers come from committed scripts.

| # | Issue found | Resolution | Evidence |
|---|---|---|---|
| 1 | Coverage was described as exactly 1-alpha; cross-fitted CQR only guarantees 1-2alpha in the worst case. | Methods §4.2 now states the CV+-type guarantee and what it does not cover. | `paper/main.tex` §4.2 |
| 2 | Flags were called a "known false-alarm rate". They are measured relative to the map's own distribution, not against the truth. | Wording corrected in the paper, IEEE report, one-pager and Word doc. | — |
| 3 | Two-sided interval tails were used as one-sided flags. | J1: a one-sided 5% lower bound flags 5.1% of tracts, almost the same set (Jaccard 0.98). | `scripts/15_journal_checks.py`, `outputs/tables/journal/` |
| 4 | Flag sets were never tested across random seeds. | J2: across 10 seeds, flag sets overlap 0.71–0.76; the 375 flags that appear under ≥9 seeds are more precise (lift 6.3 vs 5.0). | J2 |
| 5 | Region transfer under-covers (LORO 77.6–94.4%). | J3: recalibrating on 50 local tracts, which needs only the map's counts, gives 90.0–90.4%. Reported as a limit with a fix, not as a guarantee. | J3 |
| 6 | Hidden exposure was only model-based. | J4: a reference-based version is larger (wildfire rural 13.84x vs model 4.8x); missing features are not themselves vulnerability. | J4 |
| 7 | The 80% gap threshold was arbitrary. | J5: the score ordering holds at 70, 80 and 90%. | J5 |
| 8 | "Companion score ranks real gaps best" was one-sided. | J6: a log-linear GLM gives the higher ROC-AUC (0.75); the flexible model gives the higher PR-AUC (0.137 vs 0.063). Both are reported. | J6 |
| 9 | Rural was defined inconsistently (Census urban/rural in R2 vs RUCA in the pre-registered audit). | R2/J4 now use RUCA ≥ 4 as pre-registered: rural reference excess 3.72x (2.64x under the Census class). | `scripts/14_reference_validation.py`; prereg deviation 6 |
| 10 | The tract count differed (9,794 vs 9,788). | Reconciled: 1 tract has no reference count and 5 have fewer than 10 reference buildings. | Data section |
| 11 | The 8-method baseline table was dropped from the short report. | Restored. | `deliverables/ieee/IEEE_Report.tex` |

Confirmatory results are H1–H5 (pre-registered, BH-FDR). Everything labelled N, R or J is exploratory.
