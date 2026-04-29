"""Create strict patient-level stratified folds for the TCGA-CRC MSI project."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sklearn.model_selection import StratifiedKFold


PROJECT_DIR = Path(__file__).resolve().parents[1]
ANNOTATIONS_IN = PROJECT_DIR / "annotations" / "tcga_crc_msi_annotations.csv"
TEMPLATE = PROJECT_DIR / "annotations" / "annotations_template.csv"
ANNOTATIONS_OUT = ANNOTATIONS_IN

N_FOLDS = 5
SEED = 310
PATIENT_COL = "patient"
LABEL_COL = "msi_status"


def main() -> None:
    if not ANNOTATIONS_IN.exists():
        raise FileNotFoundError(
            f"Create {ANNOTATIONS_IN} first. Use {TEMPLATE} as the column template."
        )

    df = pd.read_csv(ANNOTATIONS_IN)
    required = {"slide", PATIENT_COL, LABEL_COL}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required annotation columns: {sorted(missing)}")

    labels = (
        df[[PATIENT_COL, LABEL_COL]]
        .drop_duplicates()
        .sort_values(PATIENT_COL)
        .reset_index(drop=True)
    )
    repeated = labels[PATIENT_COL].duplicated(keep=False)
    if repeated.any():
        bad = sorted(labels.loc[repeated, PATIENT_COL].unique())
        raise ValueError(f"Patients with conflicting labels: {bad[:10]}")

    counts = labels[LABEL_COL].value_counts()
    if counts.min() < N_FOLDS:
        raise ValueError(
            f"Need at least {N_FOLDS} patients in each class for stratified folds; got {counts.to_dict()}."
        )

    splitter = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
    labels["fold"] = 0
    for fold_idx, (_, val_idx) in enumerate(
        splitter.split(labels[PATIENT_COL], labels[LABEL_COL]), start=1
    ):
        labels.loc[val_idx, "fold"] = fold_idx

    fold_map = dict(zip(labels[PATIENT_COL], labels["fold"]))
    df["fold"] = df[PATIENT_COL].map(fold_map).astype(int)
    df.to_csv(ANNOTATIONS_OUT, index=False)

    summary = (
        df[[PATIENT_COL, LABEL_COL, "fold"]]
        .drop_duplicates()
        .pivot_table(index="fold", columns=LABEL_COL, values=PATIENT_COL, aggfunc="count", fill_value=0)
    )
    print(f"Wrote patient-level folds to {ANNOTATIONS_OUT}")
    print(summary)


if __name__ == "__main__":
    main()
