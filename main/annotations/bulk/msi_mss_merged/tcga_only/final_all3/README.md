# Final All-3 TCGA MSI MSS Merge

This folder contains the final TCGA-only MSI/MSS merge built from all three TCGA colorectal cBioPortal studies:

- `coadread_tcga`
- `coadread_tcga_pub`
- `coadread_tcga_pan_can_atlas_2018`

## Final label rule

1. Use direct `MSI_STATUS` from `coadread_tcga_pub` when available.
2. Otherwise use the PanCancer score-derived MSI label from the repo MSI score table.
3. Always enrich rows with `coadread_tcga` legacy columns when matching sample metadata exists.

## Files

- `tcga_all3_final_compact.csv`
  - main final table for typical analysis
- `tcga_all3_final_full.csv`
  - final table with prefixed columns from all three sources
- `tcga_all3_final_msi_h_only.csv`
  - MSI-H subset
- `tcga_all3_final_mss_only.csv`
  - MSS subset
- `tcga_all3_label_conflicts.csv`
  - samples where direct pub and PanCancer-derived labels disagree
- `tcga_all3_final_summary.json`
  - counts and precedence summary

## Important note

There is `1` direct-label conflict in this merged set:

- `TCGA-AG-A008-01`

For the final merged label, the direct `coadread_tcga_pub` label was given priority over the PanCancer-derived label.
