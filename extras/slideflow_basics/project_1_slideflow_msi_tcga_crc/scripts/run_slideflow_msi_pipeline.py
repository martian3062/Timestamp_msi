"""Run the Slideflow TCGA-CRC MSI weakly supervised MIL pipeline.

Stages can be run independently:
  setup, tiles, features, train, aggregate, all

The script intentionally keeps paths local to this project folder and requires
the user-provided TCGA slides/annotations to exist before heavy stages run.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import auc, roc_auc_score, roc_curve


PROJECT_DIR = Path(__file__).resolve().parents[1]
SF_ROOT = PROJECT_DIR / "slideflow_project"
ANNOTATIONS = PROJECT_DIR / "annotations" / "tcga_crc_msi_annotations.csv"
SLIDES_DIR = SF_ROOT / "data" / "slides"
BAGS_DIR = SF_ROOT / "bags" / "uni_v2_256px_128um"
RESULTS_DIR = SF_ROOT / "results"

OUTCOME = "msi_status"
POS_LABEL = "MSI-H"
NEG_LABEL = "MSS"
TILE_PX = 256
TILE_UM = 128
N_FOLDS = 5


def require_inputs() -> pd.DataFrame:
    if not ANNOTATIONS.exists():
        raise FileNotFoundError(f"Missing annotations: {ANNOTATIONS}")
    if not SLIDES_DIR.exists():
        raise FileNotFoundError(f"Missing slides directory: {SLIDES_DIR}")
    df = pd.read_csv(ANNOTATIONS)
    required = {"slide", "patient", OUTCOME, "fold"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Missing annotation columns: {sorted(missing)}")
    bad = sorted(set(df[OUTCOME]) - {POS_LABEL, NEG_LABEL})
    if bad:
        raise ValueError(f"Unexpected MSI labels: {bad}; expected {POS_LABEL}/{NEG_LABEL}")
    return df


def import_slideflow():
    import slideflow as sf

    return sf


def load_or_create_project():
    sf = import_slideflow()
    SF_ROOT.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    dataset_config = SF_ROOT / "datasets.json"

    try:
        project = sf.Project(str(SF_ROOT))
    except Exception:
        project = sf.Project(
            str(SF_ROOT),
            name="TCGA_CRC_MSI_Slideflow",
            annotations=str(ANNOTATIONS),
            sources=["tcga_crc_dx"],
            create=True,
        )

    if not dataset_config.exists():
        project.add_source(
            "tcga_crc_dx",
            slides=str(SLIDES_DIR),
            tfrecords=str(SF_ROOT / "tfrecords"),
            tiles=str(SF_ROOT / "tiles"),
        )
    return project


def make_dataset(project, filters=None):
    return project.dataset(
        tile_px=TILE_PX,
        tile_um=TILE_UM,
        filters=filters,
        filter_blank=OUTCOME,
        verification="both",
    )


def setup() -> None:
    df = require_inputs()
    project = load_or_create_project()
    print(project)
    print(df[[OUTCOME, "patient"]].drop_duplicates()[OUTCOME].value_counts())


def extract_tiles() -> None:
    require_inputs()
    project = load_or_create_project()
    dataset = make_dataset(project)
    dataset.extract_tiles(
        tile_px=TILE_PX,
        tile_um=TILE_UM,
        qc="both",
        normalizer="macenko",
    )


def build_extractor(sf):
    for name in ("uni_v2", "uni"):
        try:
            print(f"Trying feature extractor: {name}")
            return sf.build_feature_extractor(name, resize=True, mixed_precision=True)
        except Exception as exc:
            print(f"Could not initialize {name}: {exc}")
    raise RuntimeError("No UNI feature extractor could be initialized.")


def generate_features() -> None:
    require_inputs()
    sf = import_slideflow()
    project = load_or_create_project()
    dataset = make_dataset(project)
    extractor = build_extractor(sf)
    BAGS_DIR.mkdir(parents=True, exist_ok=True)
    project.generate_feature_bags(extractor, dataset, outdir=str(BAGS_DIR))


def train() -> None:
    require_inputs()
    sf = import_slideflow()
    project = load_or_create_project()
    dataset = make_dataset(project)

    for model_name in ("transmil", "attention_mil"):
        try:
            config = sf.mil.mil_config(model_name, lr=1e-4, epochs=20)
            print(f"Using MIL model: {model_name}")
            break
        except Exception as exc:
            print(f"Could not configure {model_name}: {exc}")
    else:
        raise RuntimeError("No MIL model could be configured.")

    for fold in range(1, N_FOLDS + 1):
        train_ds, val_ds = dataset.split(
            model_type="classification",
            labels=OUTCOME,
            val_strategy="k-fold-manual",
            val_k_fold_header="fold",
            k_fold_iter=fold,
            splits=str(SF_ROOT / "splits.json"),
        )
        project.train_mil(
            config=config,
            train_dataset=train_ds,
            val_dataset=val_ds,
            outcomes=OUTCOME,
            bags=str(BAGS_DIR),
            exp_label=f"msi_{model_name}_fold_{fold}",
            attention_heatmaps=True,
            cmap="magma",
            interpolation=None,
        )


def find_prediction_files() -> list[Path]:
    candidates = list(SF_ROOT.glob("**/*pred*.parquet")) + list(SF_ROOT.glob("**/*pred*.csv"))
    return sorted(p for p in candidates if "fold" in str(p).lower() or "mil" in str(p).lower())


def read_table(path: Path) -> pd.DataFrame:
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


def infer_score_column(df: pd.DataFrame) -> str:
    preferred = [
        POS_LABEL,
        f"y_pred_{POS_LABEL}",
        "y_pred1",
        "prob_MSI-H",
        "prob_msi_h",
        "prediction",
    ]
    for col in preferred:
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            return col
    numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    raise ValueError(f"Could not infer positive-class score column. Numeric columns: {numeric}")


def aggregate() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    curves = []

    for path in find_prediction_files():
        df = read_table(path)
        if OUTCOME not in df.columns:
            continue
        score_col = infer_score_column(df)
        y_true = (df[OUTCOME] == POS_LABEL).astype(int).to_numpy()
        y_score = df[score_col].to_numpy()
        if len(np.unique(y_true)) < 2:
            continue
        fold = next((int(part.split("_")[-1]) for part in path.parts if part.startswith("msi_") and "fold_" in part), None)
        fold = fold or len(rows) + 1
        fold_auc = roc_auc_score(y_true, y_score)
        fpr, tpr, _ = roc_curve(y_true, y_score)
        rows.append({"fold": fold, "n": len(df), "score_column": score_col, "auroc": fold_auc, "file": str(path)})
        curves.append(pd.DataFrame({"fold": fold, "fpr": fpr, "tpr": tpr}))

    if not rows:
        raise FileNotFoundError("No usable MIL prediction files found. Run the train stage first.")

    table = pd.DataFrame(rows).sort_values("fold")
    table.to_csv(RESULTS_DIR / "cv_auroc_table.csv", index=False)
    if curves:
        pd.concat(curves).to_csv(RESULTS_DIR / "roc_curves.csv", index=False)

    summary = {
        "mean_auroc": float(table["auroc"].mean()),
        "sd_auroc": float(table["auroc"].std(ddof=1)),
        "folds": int(len(table)),
    }
    (RESULTS_DIR / "cv_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(table)
    print(summary)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stage",
        choices=["setup", "tiles", "features", "train", "aggregate", "all"],
        default="setup",
    )
    args = parser.parse_args()

    if args.stage in {"setup", "all"}:
        setup()
    if args.stage in {"tiles", "all"}:
        extract_tiles()
    if args.stage in {"features", "all"}:
        generate_features()
    if args.stage in {"train", "all"}:
        train()
    if args.stage in {"aggregate", "all"}:
        aggregate()


if __name__ == "__main__":
    main()
