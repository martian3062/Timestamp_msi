"""Complete end-to-end Slideflow MSI pipeline with slide download, training, and output collection.

Usage on VM:
    python scripts/run_complete_pipeline.py --stage all
    python scripts/run_complete_pipeline.py --stage download
    python scripts/run_complete_pipeline.py --stage visualize
"""

from __future__ import annotations

# Fix for common conda/libvips library conflicts on Linux VMs
# We try to force-load the correct libjpeg to solve the 'jpeg12_write_raw_data' error
import os
import subprocess

try:
    # Try to find a working libjpeg in the environment
    env_lib = "/opt/miniforge3/envs/pathology310/lib"
    if os.path.exists(f"{env_lib}/libjpeg.so"):
        os.environ['LD_PRELOAD'] = f"{env_lib}/libjpeg.so"
    os.environ['LD_LIBRARY_PATH'] = f"{env_lib}:" + os.environ.get('LD_LIBRARY_PATH', '')
except:
    pass

import argparse
import csv
import json
import shutil
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Fix for common conda/libvips library conflicts on Linux VMs
os.environ['LD_LIBRARY_PATH'] = '/opt/miniforge3/envs/pathology310/lib:' + os.environ.get('LD_LIBRARY_PATH', '')

import numpy as np
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
ANNOTATIONS = PROJECT_DIR / "annotations" / "tcga_crc_msi_annotations.csv"
MANIFEST = PROJECT_DIR / "annotations" / "gdc_manifest_tcga_crc_msi.tsv"
SF_ROOT = PROJECT_DIR / "slideflow_project"
SLIDES_DIR = SF_ROOT / "data" / "slides"
BAGS_DIR = SF_ROOT / "bags" / "uni_v2_256px_128um"
OUTPUT_DIR = PROJECT_DIR / "output"
RESULTS_DIR = OUTPUT_DIR / "results"
FIGURES_DIR = OUTPUT_DIR / "figures"
MODELS_DIR = OUTPUT_DIR / "models"
HEATMAPS_DIR = OUTPUT_DIR / "heatmaps"

OUTCOME = "msi_status"
POS_LABEL = "MSI-H"
NEG_LABEL = "MSS"
TILE_PX = 256
TILE_UM = 128
N_FOLDS = 5

GDC_DATA_URL = "https://api.gdc.cancer.gov/data/{file_id}"


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def ensure_dirs():
    for d in [OUTPUT_DIR, RESULTS_DIR, FIGURES_DIR, MODELS_DIR, HEATMAPS_DIR,
              SLIDES_DIR, BAGS_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {OUTPUT_DIR}")


def require_inputs() -> pd.DataFrame:
    if not ANNOTATIONS.exists():
        raise FileNotFoundError(f"Missing annotations: {ANNOTATIONS}")
    df = pd.read_csv(ANNOTATIONS)
    required = {"slide", "patient", OUTCOME, "fold"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Missing annotation columns: {sorted(missing)}")
    return df


# ---------------------------------------------------------------------------
#  Stage 1: Download slides from GDC
# ---------------------------------------------------------------------------

def download_single_file(file_id, filename, expected_size, outdir, retries=5):
    outdir.mkdir(parents=True, exist_ok=True)
    destination = outdir / filename
    partial = destination.with_suffix(destination.suffix + ".part")

    if destination.exists() and expected_size and destination.stat().st_size == expected_size:
        print(f"  SKIP (already complete): {destination.name}")
        return True

    if partial.exists():
        partial.unlink()

    url = GDC_DATA_URL.format(file_id=file_id)
    for attempt in range(1, retries + 1):
        try:
            print(f"  DOWNLOAD {filename} (attempt {attempt}/{retries})")
            req = Request(url, headers={"User-Agent": "pathology310-pipeline"})
            with urlopen(req, timeout=300) as resp, partial.open("wb") as f:
                downloaded = 0
                while True:
                    chunk = resp.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if downloaded % (50 * 1024 * 1024) == 0:
                        print(f"    {downloaded / 1024**3:.2f} GB downloaded...")
            if expected_size and partial.stat().st_size != expected_size:
                raise IOError(f"Size mismatch: got {partial.stat().st_size}, expected {expected_size}")
            partial.replace(destination)
            print(f"  DONE: {destination.name}")
            return True
        except (HTTPError, URLError, TimeoutError, IOError) as exc:
            print(f"  ERROR: {exc}")
            if partial.exists():
                partial.unlink()
            if attempt == retries:
                print(f"  FAILED after {retries} attempts: {filename}")
                return False
            time.sleep(30 * attempt)
    return False


def download_slides():
    print("\n" + "=" * 70)
    print("STAGE 1: DOWNLOADING SLIDES FROM GDC")
    print("=" * 70)

    if not MANIFEST.exists():
        raise FileNotFoundError(f"Missing manifest: {MANIFEST}")

    with MANIFEST.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))

    total_bytes = sum(int(r.get("size") or 0) for r in rows)
    print(f"Slides to download: {len(rows)}")
    print(f"Expected total size: {total_bytes / 1024**3:.2f} GB")
    print(f"Destination: {SLIDES_DIR}\n")

    success, failed = 0, 0
    for idx, row in enumerate(rows, 1):
        print(f"[{idx}/{len(rows)}]")
        ok = download_single_file(
            file_id=row["id"],
            filename=row["filename"],
            expected_size=int(row.get("size") or 0),
            outdir=SLIDES_DIR,
        )
        if ok:
            success += 1
        else:
            failed += 1

    print(f"\nDownload complete: {success} OK, {failed} failed out of {len(rows)}")
    return failed == 0


# ---------------------------------------------------------------------------
#  Stage 2: Slideflow setup + tile extraction
# ---------------------------------------------------------------------------

def import_slideflow():
    import slideflow as sf
    try:
        # Using NVIDIA cuCIM for GPU-accelerated reading (bypasses broken libvips)
        sf.set_backend('cucim')
        print("Using NVIDIA cuCIM GPU-accelerated backend.")
    except Exception as e:
        try:
            sf.set_backend('opencv')
            print("Using OpenCV fallback backend.")
        except:
            print(f"Note: Backend set attempt: {e}")
    return sf


def load_or_create_project():
    sf = import_slideflow()
    SF_ROOT.mkdir(parents=True, exist_ok=True)

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

    dataset_config = SF_ROOT / "datasets.json"
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


def setup_and_tiles():
    print("\n" + "=" * 70)
    print("STAGE 2: SETUP + TILE EXTRACTION")
    print("=" * 70)

    df = require_inputs()
    project = load_or_create_project()
    print(project)

    counts = df[["patient", OUTCOME]].drop_duplicates()[OUTCOME].value_counts()
    print(f"\nPatient counts:\n{counts}\n")

    dataset = make_dataset(project)
    print("Extracting tiles (256px, 128um, QC=both, Macenko normalization)...")
    dataset.extract_tiles(
        tile_px=TILE_PX,
        tile_um=TILE_UM,
        qc="both",
        normalizer="macenko",
    )
    print("Tile extraction complete.")


# ---------------------------------------------------------------------------
#  Stage 3: Feature bag generation
# ---------------------------------------------------------------------------

def build_extractor(sf):
    # Order of preference: Simplest/Open source first for easy integration
    extractors_to_try = ["resnet50_imagenet", "virchow", "uni_v2", "uni"]
    for name in extractors_to_try:
        try:
            print(f"  [STATUS] Attempting to load feature extractor: {name} (tile_px={TILE_PX})...")
            return sf.build_feature_extractor(name, tile_px=TILE_PX, resize=True, mixed_precision=True), name
        except Exception as exc:
            print(f"  [INFO] Could not initialize {name}: {exc}")
    
    raise RuntimeError(f"Failed to initialize any of the preferred extractors ({extractors_to_try}).")


def generate_features():
    print("\n" + "=" * 70)
    print("STAGE 3: FEATURE BAG GENERATION (UNI/UNI-v2)")
    print("=" * 70)

    require_inputs()
    sf = import_slideflow()
    project = load_or_create_project()
    dataset = make_dataset(project)
    extractor, extractor_name = build_extractor(sf)
    BAGS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Using extractor: {extractor_name}")
    print(f"Bags output: {BAGS_DIR}")
    project.generate_feature_bags(extractor, dataset, outdir=str(BAGS_DIR))
    print("Feature bag generation complete.")


# ---------------------------------------------------------------------------
#  Stage 4: 5-fold MIL training
# ---------------------------------------------------------------------------

def train_mil():
    print("\n" + "=" * 70)
    print("STAGE 4: 5-FOLD MIL TRAINING")
    print("=" * 70)

    require_inputs()
    sf = import_slideflow()
    project = load_or_create_project()
    dataset = make_dataset(project)

    config = None
    model_name = None
    
    # Get MIL toolset
    if hasattr(sf, 'mil'):
        mil_tools = sf.mil
    elif hasattr(sf, 'model') and hasattr(sf.model, 'mil'):
        mil_tools = sf.model.mil
    else:
        try:
            import slideflow.mil as mil_tools
        except ImportError:
            raise RuntimeError("Slideflow MIL module not found. Please ensure slideflow[mil] is installed.")

    for name in ("transmil", "attention_mil"):
        try:
            config = mil_tools.mil_config(name, lr=1e-4, epochs=20)
            model_name = name
            print(f"Using MIL model: {name}")
            break
        except Exception as exc:
            print(f"Could not configure {name}: {exc}")

    if config is None:
        raise RuntimeError("No MIL model could be configured.")

    for fold in range(1, N_FOLDS + 1):
        print(f"\n--- Fold {fold}/{N_FOLDS} ---")
        # Handles both older and newer Slideflow parameter names for manual k-folds
        split_params = {
            "model_type": "classification",
            "labels": OUTCOME,
            "val_strategy": "k-fold-manual",
            "k_fold_iter": fold,
            "splits": str(SF_ROOT / "splits.json"),
        }
        # Try both common parameter names
        if fold > 0:
            split_params["k_fold_header"] = "fold"
            
        try:
            train_ds, val_ds = dataset.split(**split_params)
        except TypeError:
            split_params["val_k_fold_header"] = "fold"
            del split_params["k_fold_header"]
            train_ds, val_ds = dataset.split(**split_params)
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

    print("\nMIL training complete for all folds.")


# ---------------------------------------------------------------------------
#  Stage 5: Aggregate results
# ---------------------------------------------------------------------------

def aggregate_results():
    print("\n" + "=" * 70)
    print("STAGE 5: AGGREGATE RESULTS")
    print("=" * 70)

    from sklearn.metrics import (
        auc, roc_auc_score, roc_curve,
        precision_recall_curve, average_precision_score,
        confusion_matrix, classification_report,
    )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    pred_files = sorted(
        list(SF_ROOT.glob("**/*pred*.parquet")) + list(SF_ROOT.glob("**/*pred*.csv"))
    )
    print(f"Found {len(pred_files)} prediction files")

    rows = []
    curves_roc = []
    curves_pr = []
    all_preds = []
    confusion_matrices = []

    for path in pred_files:
        df = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path)
        if OUTCOME not in df.columns:
            continue

        # Find score column
        score_col = None
        for col in [POS_LABEL, f"y_pred_{POS_LABEL}", "y_pred1", "prob_MSI-H", "prediction"]:
            if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                score_col = col
                break
        if score_col is None:
            continue

        y_true = (df[OUTCOME] == POS_LABEL).astype(int).to_numpy()
        y_score = df[score_col].to_numpy()
        if len(np.unique(y_true)) < 2:
            continue

        # Infer fold
        fold = None
        for part in path.parts:
            if "fold_" in part:
                try:
                    fold = int(part.split("fold_")[-1].split("_")[0].split("/")[0])
                except ValueError:
                    pass
        fold = fold or (len(rows) + 1)

        # ROC
        fpr, tpr, _ = roc_curve(y_true, y_score)
        fold_auc = roc_auc_score(y_true, y_score)

        # PR
        precision, recall, _ = precision_recall_curve(y_true, y_score)
        ap = average_precision_score(y_true, y_score)

        # Confusion matrix at 0.5 threshold
        y_pred_binary = (y_score >= 0.5).astype(int)
        cm = confusion_matrix(y_true, y_pred_binary)

        rows.append({
            "fold": fold, "n": len(df), "score_column": score_col,
            "auroc": fold_auc, "auprc": ap, "file": str(path),
        })
        curves_roc.append(pd.DataFrame({"fold": fold, "fpr": fpr, "tpr": tpr}))
        curves_pr.append(pd.DataFrame({"fold": fold, "precision": precision, "recall": recall}))
        confusion_matrices.append({"fold": fold, "cm": cm.tolist()})

        df_pred = df[[OUTCOME]].copy()
        df_pred["score"] = y_score
        df_pred["y_true"] = y_true
        df_pred["fold"] = fold
        if "patient" in df.columns:
            df_pred["patient"] = df["patient"]
        if "slide" in df.columns:
            df_pred["slide"] = df["slide"]
        all_preds.append(df_pred)

    if not rows:
        print("No prediction files found yet. Skipping aggregation.")
        return None

    table = pd.DataFrame(rows).sort_values("fold")
    table.to_csv(RESULTS_DIR / "cv_auroc_table.csv", index=False)

    if curves_roc:
        pd.concat(curves_roc).to_csv(RESULTS_DIR / "roc_curves.csv", index=False)
    if curves_pr:
        pd.concat(curves_pr).to_csv(RESULTS_DIR / "pr_curves.csv", index=False)
    if all_preds:
        pd.concat(all_preds).to_csv(RESULTS_DIR / "all_predictions.csv", index=False)

    summary = {
        "mean_auroc": float(table["auroc"].mean()),
        "sd_auroc": float(table["auroc"].std(ddof=1)),
        "mean_auprc": float(table["auprc"].mean()),
        "sd_auprc": float(table["auprc"].std(ddof=1)),
        "folds": int(len(table)),
        "total_samples": int(table["n"].sum()),
        "confusion_matrices": confusion_matrices,
    }
    (RESULTS_DIR / "cv_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"\n{table.to_string(index=False)}")
    print(f"\nMean AUROC: {summary['mean_auroc']:.4f} ± {summary['sd_auroc']:.4f}")
    print(f"Mean AUPRC: {summary['mean_auprc']:.4f} ± {summary['sd_auprc']:.4f}")
    print(f"\nResults saved to: {RESULTS_DIR}")

    return summary


# ---------------------------------------------------------------------------
#  Stage 6: Copy outputs
# ---------------------------------------------------------------------------

def collect_outputs():
    print("\n" + "=" * 70)
    print("STAGE 6: COLLECTING OUTPUTS")
    print("=" * 70)

    # Copy model weights
    for src in SF_ROOT.glob("**/mil_*/**/*.pth"):
        dst = MODELS_DIR / src.name
        if not dst.exists():
            shutil.copy2(src, dst)
            print(f"  Copied model: {src.name}")

    # Copy heatmaps
    for src in SF_ROOT.glob("**/*heatmap*"):
        if src.is_file():
            dst = HEATMAPS_DIR / src.name
            if not dst.exists():
                shutil.copy2(src, dst)
                print(f"  Copied heatmap: {src.name}")

    # Copy attention arrays
    for src in SF_ROOT.glob("**/*attention*"):
        if src.is_file() and src.suffix in (".npz", ".npy", ".pt", ".png", ".jpg"):
            dst = HEATMAPS_DIR / src.name
            if not dst.exists():
                shutil.copy2(src, dst)
                print(f"  Copied attention: {src.name}")

    # Copy annotations
    ann_out = OUTPUT_DIR / "annotations"
    ann_out.mkdir(exist_ok=True)
    for src in (PROJECT_DIR / "annotations").glob("*.csv"):
        shutil.copy2(src, ann_out / src.name)
    for src in (PROJECT_DIR / "annotations").glob("*.tsv"):
        shutil.copy2(src, ann_out / src.name)
    print(f"  Copied annotation files")

    # Copy config
    cfg_out = OUTPUT_DIR / "configs"
    cfg_out.mkdir(exist_ok=True)
    for src in (PROJECT_DIR / "configs").glob("*.yaml"):
        shutil.copy2(src, cfg_out / src.name)

    print(f"\nAll outputs collected in: {OUTPUT_DIR}")


# ---------------------------------------------------------------------------
#  Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Complete Slideflow MSI Pipeline")
    parser.add_argument(
        "--stage",
        choices=["download", "tiles", "features", "train", "aggregate",
                 "visualize", "collect", "all", "post_train"],
        default="all",
        help="Pipeline stage to run",
    )
    args = parser.parse_args()

    ensure_dirs()

    if args.stage in {"download", "all"}:
        download_slides()

    if args.stage in {"tiles", "all"}:
        setup_and_tiles()

    if args.stage in {"features", "all"}:
        generate_features()

    if args.stage in {"train", "all"}:
        train_mil()

    if args.stage in {"aggregate", "all", "post_train"}:
        aggregate_results()

    if args.stage in {"collect", "all", "post_train"}:
        collect_outputs()

    if args.stage in {"visualize", "all", "post_train"}:
        from generate_advanced_visualizations import generate_all_visualizations
        generate_all_visualizations(PROJECT_DIR, OUTPUT_DIR)

    print("\n" + "=" * 70)
    print("PIPELINE COMPLETE")
    print(f"All outputs saved to: {OUTPUT_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    main()
