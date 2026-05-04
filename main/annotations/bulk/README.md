# Bulk cBioPortal Colorectal Export

This folder contains bulk-exported annotation-style data for colorectal studies listed by cBioPortal when filtering datasets by `colorec`.

## Scope

- Source: `https://www.cbioportal.org/datasets`
- Filter used: study names containing `Colorec`
- Exported studies: `19`

## Folder layout

Each study has its own subfolder:

- `study.json`
  - study-level metadata from `/api/studies/{studyId}`
- `clinical_attributes.json`
  - full clinical attribute definitions
- `clinical_attributes.csv`
  - tabular version of attribute definitions
- `clinical_data_long.json`
  - raw long-format clinical records from `/api/studies/{studyId}/clinical-data`
- `clinical_data_long.csv`
  - normalized long-format table
- `patient_clinical_wide.csv`
  - one row per patient, attributes pivoted to columns
- `sample_clinical_wide.csv`
  - one row per sample, attributes pivoted to columns

## Root files

- `bulk_colorectal_cbioportal_index.csv`
  - one row per study with counts and folder name
- `bulk_colorectal_cbioportal_index.json`
  - JSON version of the same index
- `bulk_summary.json`
  - compact export summary

## Notes

- These are cBioPortal clinical and study annotation exports, not WSI manifests.
- `patient_clinical_wide.csv` is best for patient-level labels or cohort joins.
- `sample_clinical_wide.csv` is best for sample-level labels such as MSI, sample type, stage, or assay-linked metadata.
- Some studies contain many more clinical attributes than others.
- Not every colorectal study contains MSI-specific fields.
