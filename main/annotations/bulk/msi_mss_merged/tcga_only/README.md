# TCGA-only MSI MSS merged export

This folder contains TCGA-only colorectal MSI/MSS merged tables.

Sources used:
- coadread_tcga_pub: direct MSI_STATUS labels
- coadread_tcga_pan_can_atlas_2018: score-derived MSI labels from the repo MSI score table
- coadread_tcga: enrichment only, because it has no direct MSI label field

Files:
- tcga_only_msi_mss_merged_compact.csv
- tcga_only_msi_mss_merged_full.csv
- tcga_only_msi_h_only.csv
- tcga_only_mss_only.csv
- tcga_only_status_direct_pub.csv
- tcga_only_score_derived_pancan.csv
- tcga_only_msi_mss_summary.json
