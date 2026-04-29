"""Advanced publication-quality visualizations for the Slideflow MSI pipeline.

Generates 15+ figures covering cohort analysis, training metrics, ROC/PR curves,
confusion matrices, prediction distributions, calibration, and summary dashboards.

Can run standalone:
    python scripts/generate_advanced_visualizations.py

Or imported by run_complete_pipeline.py
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import pandas as pd

# Optional imports with fallbacks
try:
    import seaborn as sns
    HAS_SEABORN = True
except ImportError:
    HAS_SEABORN = False

try:
    from sklearn.metrics import (
        roc_curve, roc_auc_score, precision_recall_curve,
        average_precision_score, confusion_matrix, calibration_curve,
    )
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

warnings.filterwarnings("ignore", category=FutureWarning)

# ---------------------------------------------------------------------------
#  Color palette & style
# ---------------------------------------------------------------------------

PALETTE = {
    "msih":       "#E63946",   # vivid red
    "mss":        "#457B9D",   # steel blue
    "msih_light": "#FFB3B8",
    "mss_light":  "#A8DADC",
    "accent":     "#F4A261",   # amber
    "accent2":    "#2A9D8F",   # teal
    "bg_dark":    "#1D3557",   # dark navy
    "bg_light":   "#F1FAEE",   # off-white
    "grid":       "#E0E0E0",
    "text":       "#2B2D42",
    "gold":       "#FFD700",
    "fold_colors": ["#E63946", "#457B9D", "#2A9D8F", "#F4A261", "#9B59B6"],
}

FOLD_CMAP = LinearSegmentedColormap.from_list(
    "folds", PALETTE["fold_colors"], N=5
)


def setup_style():
    """Apply publication-quality matplotlib style."""
    plt.rcParams.update({
        "figure.facecolor": "#FAFAFA",
        "axes.facecolor": "#FAFAFA",
        "axes.edgecolor": "#CCCCCC",
        "axes.labelcolor": PALETTE["text"],
        "axes.titlecolor": PALETTE["text"],
        "axes.grid": True,
        "grid.color": PALETTE["grid"],
        "grid.alpha": 0.5,
        "grid.linewidth": 0.5,
        "text.color": PALETTE["text"],
        "xtick.color": PALETTE["text"],
        "ytick.color": PALETTE["text"],
        "font.size": 11,
        "axes.titlesize": 14,
        "axes.labelsize": 12,
        "figure.titlesize": 16,
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.3,
        "legend.framealpha": 0.9,
        "legend.edgecolor": "#CCCCCC",
    })
    try:
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = ["Inter", "Helvetica Neue", "Arial", "DejaVu Sans"]
    except Exception:
        pass


def add_watermark(fig, text="Slideflow MSI Pipeline"):
    """Add subtle watermark."""
    fig.text(0.99, 0.01, text, fontsize=7, color="#CCCCCC",
             ha="right", va="bottom", style="italic", alpha=0.6)


def save_fig(fig, path, close=True):
    """Save figure with consistent settings."""
    fig.savefig(path, facecolor=fig.get_facecolor())
    if close:
        plt.close(fig)
    print(f"  Saved: {path.name}")


# ═══════════════════════════════════════════════════════════════════════════
#  1. COHORT OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════

def plot_cohort_overview(df: pd.DataFrame, out: Path):
    """Donut chart + summary statistics."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle("Cohort Overview — TCGA-CRC MSI Classification", fontweight="bold", fontsize=16)

    # --- Donut chart ---
    ax = axes[0]
    counts = df[["patient", "msi_status"]].drop_duplicates()["msi_status"].value_counts()
    msih = counts.get("MSI-H", 0)
    mss = counts.get("MSS", 0)
    total = msih + mss

    wedges, texts, autotexts = ax.pie(
        [msih, mss],
        labels=["MSI-H", "MSS"],
        colors=[PALETTE["msih"], PALETTE["mss"]],
        autopct=lambda p: f"{p:.0f}%\n({int(p*total/100)})",
        startangle=90,
        pctdistance=0.75,
        wedgeprops=dict(width=0.45, edgecolor="white", linewidth=3),
        textprops=dict(fontsize=13, fontweight="bold"),
    )
    for at in autotexts:
        at.set_fontsize(11)
        at.set_color("white")
        at.set_fontweight("bold")
    ax.set_title(f"Patient Distribution (n={total})", fontsize=13, pad=15)

    # Center text
    ax.text(0, 0, f"{total}\npatients", ha="center", va="center",
            fontsize=16, fontweight="bold", color=PALETTE["text"])

    # --- Summary stats table ---
    ax = axes[1]
    ax.axis("off")

    slide_counts = df["msi_status"].value_counts()
    sites = df["site"].nunique() if "site" in df.columns else "N/A"

    table_data = [
        ["Total Patients", str(total)],
        ["Total Slides", str(len(df))],
        ["MSI-H Patients", str(msih)],
        ["MSS Patients", str(mss)],
        ["Unique Sites", str(sites)],
        ["MSI-H Slides", str(slide_counts.get("MSI-H", 0))],
        ["MSS Slides", str(slide_counts.get("MSS", 0))],
        ["Cross-Val Folds", str(df["fold"].nunique()) if "fold" in df.columns else "N/A"],
        ["Class Ratio", f"1:{mss/msih:.1f}" if msih > 0 else "N/A"],
    ]

    table = ax.table(
        cellText=table_data,
        colLabels=["Metric", "Value"],
        loc="center",
        cellLoc="center",
        colWidths=[0.5, 0.3],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.0, 1.8)

    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor("#E0E0E0")
        if row == 0:
            cell.set_facecolor(PALETTE["bg_dark"])
            cell.set_text_props(color="white", fontweight="bold")
        elif row % 2 == 0:
            cell.set_facecolor("#F8F8FF")
        else:
            cell.set_facecolor("white")

    ax.set_title("Cohort Summary", fontsize=13, pad=15)

    add_watermark(fig)
    fig.tight_layout(rect=[0, 0.02, 1, 0.94])
    save_fig(fig, out / "01_cohort_overview.png")


# ═══════════════════════════════════════════════════════════════════════════
#  2. FOLD DISTRIBUTION
# ═══════════════════════════════════════════════════════════════════════════

def plot_fold_distribution(df: pd.DataFrame, out: Path):
    """Grouped bar chart of class counts per fold."""
    if "fold" not in df.columns:
        return

    fig, ax = plt.subplots(figsize=(12, 6))
    fig.suptitle("Patient-Level Fold Distribution", fontweight="bold", fontsize=16)

    patients = df[["patient", "msi_status", "fold"]].drop_duplicates()
    pivot = patients.pivot_table(
        index="fold", columns="msi_status", values="patient", aggfunc="count", fill_value=0
    )

    x = np.arange(len(pivot))
    width = 0.35

    bars1 = ax.bar(x - width/2, pivot.get("MSI-H", [0]*len(pivot)), width,
                   color=PALETTE["msih"], label="MSI-H", edgecolor="white",
                   linewidth=1.5, zorder=3)
    bars2 = ax.bar(x + width/2, pivot.get("MSS", [0]*len(pivot)), width,
                   color=PALETTE["mss"], label="MSS", edgecolor="white",
                   linewidth=1.5, zorder=3)

    # Value labels
    for bars in [bars1, bars2]:
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, h + 0.15,
                    str(int(h)), ha="center", va="bottom",
                    fontweight="bold", fontsize=11, color=PALETTE["text"])

    ax.set_xlabel("Fold", fontweight="bold")
    ax.set_ylabel("Number of Patients", fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([f"Fold {i}" for i in pivot.index])
    ax.legend(fontsize=12, loc="upper right")
    ax.set_ylim(0, max(pivot.max()) * 1.3)
    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))

    # Add ratio annotation
    for i, fold in enumerate(pivot.index):
        msih_count = pivot.get("MSI-H", pd.Series([0]*len(pivot))).iloc[i] if "MSI-H" in pivot.columns else 0
        mss_count = pivot.get("MSS", pd.Series([0]*len(pivot))).iloc[i] if "MSS" in pivot.columns else 0
        total = msih_count + mss_count
        ax.text(i, -0.8, f"n={total}", ha="center", fontsize=9, color="#888888")

    add_watermark(fig)
    fig.tight_layout(rect=[0, 0.02, 1, 0.94])
    save_fig(fig, out / "02_fold_distribution.png")


# ═══════════════════════════════════════════════════════════════════════════
#  3. SITE DISTRIBUTION
# ═══════════════════════════════════════════════════════════════════════════

def plot_site_distribution(df: pd.DataFrame, out: Path):
    """Horizontal stacked bar chart of MSI status per TCGA site."""
    if "site" not in df.columns:
        return

    fig, ax = plt.subplots(figsize=(12, 8))
    fig.suptitle("TCGA Site Distribution by MSI Status", fontweight="bold", fontsize=16)

    patients = df[["patient", "msi_status", "site"]].drop_duplicates()
    pivot = patients.pivot_table(
        index="site", columns="msi_status", values="patient", aggfunc="count", fill_value=0
    )
    pivot["total"] = pivot.sum(axis=1)
    pivot = pivot.sort_values("total", ascending=True)

    y = np.arange(len(pivot))

    if "MSS" in pivot.columns:
        ax.barh(y, pivot["MSS"], color=PALETTE["mss"], label="MSS",
                edgecolor="white", linewidth=1, zorder=3)
    left = pivot.get("MSS", pd.Series([0]*len(pivot), index=pivot.index))
    if "MSI-H" in pivot.columns:
        ax.barh(y, pivot["MSI-H"], left=left, color=PALETTE["msih"],
                label="MSI-H", edgecolor="white", linewidth=1, zorder=3)

    ax.set_yticks(y)
    ax.set_yticklabels([f"TCGA-{s}" for s in pivot.index], fontsize=10)
    ax.set_xlabel("Number of Patients", fontweight="bold")
    ax.legend(fontsize=11, loc="lower right")

    # Total annotations
    for i, total in enumerate(pivot["total"]):
        ax.text(total + 0.2, i, str(int(total)), va="center", fontsize=9, color="#666")

    add_watermark(fig)
    fig.tight_layout(rect=[0, 0.02, 1, 0.94])
    save_fig(fig, out / "03_site_distribution.png")


# ═══════════════════════════════════════════════════════════════════════════
#  4. MSI SCORE DISTRIBUTIONS
# ═══════════════════════════════════════════════════════════════════════════

def plot_msi_scores(df: pd.DataFrame, out: Path):
    """KDE + strip plots for MANTIS and MSIsensor scores."""
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle("MSI Score Distributions by True Label", fontweight="bold", fontsize=16)

    score_cols = [
        ("msi_score_mantis", "MANTIS Score", 0.6, 0.4),
        ("msi_sensor_score", "MSIsensor Score", 10, 4),
    ]

    for idx, (col, title, thresh_h, thresh_l) in enumerate(score_cols):
        ax = axes[idx]
        if col not in df.columns:
            ax.text(0.5, 0.5, f"Column '{col}' not found", transform=ax.transAxes,
                    ha="center", va="center")
            continue

        for label, color in [("MSI-H", PALETTE["msih"]), ("MSS", PALETTE["mss"])]:
            vals = df.loc[df["msi_status"] == label, col].dropna()
            if len(vals) == 0:
                continue

            # KDE
            try:
                from scipy.stats import gaussian_kde
                kde = gaussian_kde(vals, bw_method=0.3)
                val_range = vals.max() - vals.min()
                x_range = np.linspace(vals.min() - 0.1 * val_range, vals.max() + 0.1 * val_range, 200)
                ax.fill_between(x_range, kde(x_range), alpha=0.3, color=color, zorder=2)
                ax.plot(x_range, kde(x_range), color=color, linewidth=2, label=label, zorder=3)
            except ImportError:
                ax.hist(vals, bins=15, alpha=0.5, color=color, label=label, density=True, zorder=2)

            # Strip
            jitter = np.random.uniform(-0.01, 0.01, len(vals))
            ax.scatter(vals, jitter - 0.05 * (1 if label == "MSI-H" else 2),
                       c=color, alpha=0.6, s=25, edgecolors="white", linewidth=0.5, zorder=4)

        # Threshold lines
        ax.axvline(thresh_h, color=PALETTE["msih"], linestyle="--", alpha=0.7, linewidth=1.5,
                   label=f"MSI-H threshold ({thresh_h})")
        ax.axvline(thresh_l, color=PALETTE["mss"], linestyle="--", alpha=0.7, linewidth=1.5,
                   label=f"MSS threshold ({thresh_l})")

        ax.set_title(title, fontweight="bold")
        ax.set_xlabel(title)
        ax.set_ylabel("Density")
        ax.legend(fontsize=9, loc="upper right")

    add_watermark(fig)
    fig.tight_layout(rect=[0, 0.02, 1, 0.94])
    save_fig(fig, out / "04_msi_score_distributions.png")


# ═══════════════════════════════════════════════════════════════════════════
#  5. PROJECT DISTRIBUTION (COAD vs READ)
# ═══════════════════════════════════════════════════════════════════════════

def plot_project_distribution(df: pd.DataFrame, out: Path):
    """Nested donut showing project × MSI status."""
    if "project" not in df.columns:
        return

    fig, ax = plt.subplots(figsize=(10, 8))
    fig.suptitle("TCGA Project × MSI Status Distribution", fontweight="bold", fontsize=16)

    patients = df[["patient", "msi_status", "project"]].drop_duplicates()

    # Outer ring: project
    proj_counts = patients["project"].value_counts()
    proj_colors = ["#264653", "#E76F51"]

    # Inner ring: msi_status within each project
    inner_labels = []
    inner_sizes = []
    inner_colors = []
    for proj in proj_counts.index:
        sub = patients[patients["project"] == proj]
        for status in ["MSI-H", "MSS"]:
            cnt = len(sub[sub["msi_status"] == status])
            inner_labels.append(f"{proj}\n{status}")
            inner_sizes.append(cnt)
            inner_colors.append(PALETTE["msih"] if status == "MSI-H" else PALETTE["mss"])

    # Outer ring
    ax.pie(proj_counts, labels=proj_counts.index, colors=proj_colors,
           radius=1.2, startangle=90,
           wedgeprops=dict(width=0.3, edgecolor="white", linewidth=2),
           textprops=dict(fontsize=12, fontweight="bold"))

    # Inner ring
    ax.pie(inner_sizes, labels=None, colors=inner_colors,
           radius=0.85, startangle=90,
           autopct=lambda p: f"{int(p*sum(inner_sizes)/100)}" if p > 5 else "",
           pctdistance=0.75,
           wedgeprops=dict(width=0.35, edgecolor="white", linewidth=1.5),
           textprops=dict(fontsize=9, color="white", fontweight="bold"))

    # Legend
    legend_elements = [
        mpatches.Patch(facecolor=PALETTE["msih"], label="MSI-H"),
        mpatches.Patch(facecolor=PALETTE["mss"], label="MSS"),
    ]
    ax.legend(handles=legend_elements, loc="lower right", fontsize=11)

    add_watermark(fig)
    fig.tight_layout(rect=[0, 0.02, 1, 0.94])
    save_fig(fig, out / "05_project_distribution.png")


# ═══════════════════════════════════════════════════════════════════════════
#  6. ROC CURVES (5-fold + mean)
# ═══════════════════════════════════════════════════════════════════════════

def plot_roc_curves(results_dir: Path, out: Path):
    """Publication-quality ROC curves with confidence band."""
    roc_file = results_dir / "roc_curves.csv"
    auroc_file = results_dir / "cv_auroc_table.csv"

    if not roc_file.exists():
        print("  Skipping ROC curves (no roc_curves.csv)")
        return

    fig, ax = plt.subplots(figsize=(10, 9))
    fig.suptitle("Receiver Operating Characteristic — 5-Fold Cross-Validation",
                 fontweight="bold", fontsize=16)

    roc_df = pd.read_csv(roc_file)
    auroc_df = pd.read_csv(auroc_file) if auroc_file.exists() else None

    # Per-fold curves
    mean_fpr = np.linspace(0, 1, 200)
    tprs = []

    for fold in sorted(roc_df["fold"].unique()):
        fold_data = roc_df[roc_df["fold"] == fold]
        fpr = fold_data["fpr"].values
        tpr = fold_data["tpr"].values
        color = PALETTE["fold_colors"][(fold - 1) % 5]

        fold_auc = np.trapz(tpr, fpr)
        if auroc_df is not None and fold in auroc_df["fold"].values:
            fold_auc = auroc_df.loc[auroc_df["fold"] == fold, "auroc"].values[0]

        ax.plot(fpr, tpr, color=color, alpha=0.6, linewidth=1.5,
                label=f"Fold {fold} (AUC = {fold_auc:.3f})")

        interp_tpr = np.interp(mean_fpr, fpr, tpr)
        interp_tpr[0] = 0.0
        tprs.append(interp_tpr)

    # Mean curve + confidence band
    mean_tpr = np.mean(tprs, axis=0)
    mean_tpr[-1] = 1.0
    std_tpr = np.std(tprs, axis=0)
    mean_auc = np.trapz(mean_tpr, mean_fpr)

    ax.plot(mean_fpr, mean_tpr, color=PALETTE["bg_dark"], linewidth=3,
            label=f"Mean (AUC = {mean_auc:.3f})", zorder=5)
    ax.fill_between(mean_fpr, np.clip(mean_tpr - std_tpr, 0, 1),
                    np.clip(mean_tpr + std_tpr, 0, 1),
                    alpha=0.15, color=PALETTE["bg_dark"], label="± 1 SD", zorder=4)

    # Diagonal
    ax.plot([0, 1], [0, 1], "--", color="#AAAAAA", linewidth=1, label="Random (AUC = 0.500)")

    ax.set_xlim([-0.02, 1.02])
    ax.set_ylim([-0.02, 1.02])
    ax.set_xlabel("False Positive Rate (1 − Specificity)", fontweight="bold")
    ax.set_ylabel("True Positive Rate (Sensitivity)", fontweight="bold")
    ax.legend(loc="lower right", fontsize=10, framealpha=0.95)

    # AUC annotation box
    if auroc_df is not None:
        mean_a = auroc_df["auroc"].mean()
        std_a = auroc_df["auroc"].std(ddof=1)
        ax.text(0.55, 0.15, f"Mean AUROC = {mean_a:.3f} ± {std_a:.3f}",
                transform=ax.transAxes, fontsize=13, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.5", facecolor=PALETTE["bg_light"],
                          edgecolor=PALETTE["bg_dark"], alpha=0.9))

    add_watermark(fig)
    fig.tight_layout(rect=[0, 0.02, 1, 0.94])
    save_fig(fig, out / "06_roc_curves.png")


# ═══════════════════════════════════════════════════════════════════════════
#  7. AUROC BAR CHART
# ═══════════════════════════════════════════════════════════════════════════

def plot_auroc_bar(results_dir: Path, out: Path):
    """Per-fold AUROC with mean line and gradient bars."""
    auroc_file = results_dir / "cv_auroc_table.csv"
    if not auroc_file.exists():
        print("  Skipping AUROC bar chart (no cv_auroc_table.csv)")
        return

    df = pd.read_csv(auroc_file)

    fig, ax = plt.subplots(figsize=(12, 6))
    fig.suptitle("Per-Fold AUROC Performance", fontweight="bold", fontsize=16)

    x = np.arange(len(df))
    colors = [PALETTE["fold_colors"][i % 5] for i in range(len(df))]

    bars = ax.bar(x, df["auroc"], color=colors, edgecolor="white", linewidth=2,
                  width=0.6, zorder=3)

    # Value labels
    for bar, val in zip(bars, df["auroc"]):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
                f"{val:.3f}", ha="center", va="bottom", fontweight="bold",
                fontsize=12, color=PALETTE["text"])

    # Mean line
    mean_auc = df["auroc"].mean()
    std_auc = df["auroc"].std(ddof=1)
    ax.axhline(mean_auc, color=PALETTE["bg_dark"], linewidth=2.5, linestyle="--",
               label=f"Mean = {mean_auc:.3f} ± {std_auc:.3f}", zorder=4)
    ax.axhspan(mean_auc - std_auc, mean_auc + std_auc,
               alpha=0.1, color=PALETTE["bg_dark"], zorder=1)

    ax.set_xlabel("Cross-Validation Fold", fontweight="bold")
    ax.set_ylabel("AUROC", fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([f"Fold {int(f)}" for f in df["fold"]])
    ax.set_ylim(0, min(1.05, df["auroc"].max() + 0.1))
    ax.legend(fontsize=12, loc="upper right")

    add_watermark(fig)
    fig.tight_layout(rect=[0, 0.02, 1, 0.94])
    save_fig(fig, out / "07_auroc_bar_chart.png")


# ═══════════════════════════════════════════════════════════════════════════
#  8. PRECISION-RECALL CURVES
# ═══════════════════════════════════════════════════════════════════════════

def plot_pr_curves(results_dir: Path, out: Path):
    """Precision-Recall curves per fold."""
    pr_file = results_dir / "pr_curves.csv"
    if not pr_file.exists():
        print("  Skipping PR curves (no pr_curves.csv)")
        return

    fig, ax = plt.subplots(figsize=(10, 9))
    fig.suptitle("Precision-Recall Curves — 5-Fold Cross-Validation",
                 fontweight="bold", fontsize=16)

    pr_df = pd.read_csv(pr_file)
    auroc_df_path = results_dir / "cv_auroc_table.csv"
    auroc_df = pd.read_csv(auroc_df_path) if auroc_df_path.exists() else None

    for fold in sorted(pr_df["fold"].unique()):
        fold_data = pr_df[pr_df["fold"] == fold]
        color = PALETTE["fold_colors"][(fold - 1) % 5]

        ap = np.trapz(fold_data["precision"].values, fold_data["recall"].values)
        ap = abs(ap)
        if auroc_df is not None and "auprc" in auroc_df.columns and fold in auroc_df["fold"].values:
            ap = auroc_df.loc[auroc_df["fold"] == fold, "auprc"].values[0]

        ax.plot(fold_data["recall"], fold_data["precision"],
                color=color, linewidth=1.5, alpha=0.7,
                label=f"Fold {fold} (AP = {ap:.3f})")

    ax.set_xlim([-0.02, 1.02])
    ax.set_ylim([-0.02, 1.05])
    ax.set_xlabel("Recall", fontweight="bold")
    ax.set_ylabel("Precision", fontweight="bold")
    ax.legend(loc="upper right", fontsize=10)

    add_watermark(fig)
    fig.tight_layout(rect=[0, 0.02, 1, 0.94])
    save_fig(fig, out / "08_precision_recall_curves.png")


# ═══════════════════════════════════════════════════════════════════════════
#  9. CONFUSION MATRICES
# ═══════════════════════════════════════════════════════════════════════════

def plot_confusion_matrices(results_dir: Path, out: Path):
    """Heatmap confusion matrices for each fold + aggregated."""
    summary_file = results_dir / "cv_summary.json"
    preds_file = results_dir / "all_predictions.csv"

    if not preds_file.exists():
        print("  Skipping confusion matrices (no all_predictions.csv)")
        return

    preds_df = pd.read_csv(preds_file)
    folds = sorted(preds_df["fold"].unique())
    n_folds = len(folds)

    fig, axes = plt.subplots(1, n_folds + 1, figsize=(4 * (n_folds + 1), 5))
    if n_folds + 1 == 1:
        axes = [axes]
    fig.suptitle("Confusion Matrices Per Fold (Threshold = 0.5)", fontweight="bold", fontsize=16)

    all_y_true = []
    all_y_pred = []
    labels_display = ["MSS", "MSI-H"]

    for idx, fold in enumerate(folds):
        ax = axes[idx]
        fold_data = preds_df[preds_df["fold"] == fold]
        y_true = fold_data["y_true"].values
        y_pred = (fold_data["score"].values >= 0.5).astype(int)

        all_y_true.extend(y_true)
        all_y_pred.extend(y_pred)

        cm = confusion_matrix(y_true, y_pred)
        _plot_single_cm(ax, cm, labels_display, f"Fold {fold}",
                        PALETTE["fold_colors"][(fold-1) % 5])

    # Aggregated
    ax = axes[-1]
    cm_agg = confusion_matrix(all_y_true, all_y_pred)
    _plot_single_cm(ax, cm_agg, labels_display, "Aggregated", PALETTE["bg_dark"])

    add_watermark(fig)
    fig.tight_layout(rect=[0, 0.02, 1, 0.92])
    save_fig(fig, out / "09_confusion_matrices.png")


def _plot_single_cm(ax, cm, labels, title, accent_color):
    """Draw a single confusion matrix heatmap."""
    cmap = LinearSegmentedColormap.from_list("cm", ["#FFFFFF", accent_color])
    im = ax.imshow(cm, interpolation="nearest", cmap=cmap, aspect="auto")

    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            val = cm[i, j]
            color = "white" if val > cm.max() * 0.6 else PALETTE["text"]
            ax.text(j, i, str(val), ha="center", va="center",
                    fontsize=14, fontweight="bold", color=color)

    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("Predicted", fontsize=10)
    ax.set_ylabel("Actual", fontsize=10)
    ax.set_title(title, fontweight="bold", fontsize=11)


# ═══════════════════════════════════════════════════════════════════════════
#  10. PREDICTION SCORE DISTRIBUTION
# ═══════════════════════════════════════════════════════════════════════════

def plot_prediction_distributions(results_dir: Path, out: Path):
    """Violin + swarm plot of prediction scores by true class."""
    preds_file = results_dir / "all_predictions.csv"
    if not preds_file.exists():
        print("  Skipping prediction distributions (no all_predictions.csv)")
        return

    df = pd.read_csv(preds_file)

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    fig.suptitle("Prediction Score Distributions", fontweight="bold", fontsize=16)

    # --- Panel A: By true class ---
    ax = axes[0]
    for label, color, pos in [("MSS", PALETTE["mss"], 0), ("MSI-H", PALETTE["msih"], 1)]:
        vals = df.loc[df["msi_status"] == label, "score"].values
        if len(vals) == 0:
            continue

        # Violin
        parts = ax.violinplot([vals], positions=[pos], showmeans=True,
                              showmedians=True, widths=0.7)
        for pc in parts["bodies"]:
            pc.set_facecolor(color)
            pc.set_alpha(0.4)
        for key in ["cmeans", "cmedians", "cbars", "cmins", "cmaxes"]:
            if key in parts:
                parts[key].set_color(color)

        # Jitter strip
        jitter = np.random.uniform(-0.12, 0.12, len(vals))
        ax.scatter(pos + jitter, vals, c=color, alpha=0.6, s=20,
                   edgecolors="white", linewidth=0.5, zorder=4)

    ax.axhline(0.5, color="#AAA", linestyle="--", linewidth=1, alpha=0.8)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["MSS (True)", "MSI-H (True)"], fontsize=12, fontweight="bold")
    ax.set_ylabel("MSI-H Prediction Score", fontweight="bold")
    ax.set_title("By True Class", fontweight="bold")

    # --- Panel B: By fold ---
    ax = axes[1]
    folds = sorted(df["fold"].unique())
    positions = list(range(len(folds)))

    for i, fold in enumerate(folds):
        fold_data = df[df["fold"] == fold]
        color = PALETTE["fold_colors"][(fold-1) % 5]

        for label, marker in [("MSS", "o"), ("MSI-H", "D")]:
            sub = fold_data[fold_data["msi_status"] == label]
            if len(sub) == 0:
                continue
            jitter = np.random.uniform(-0.15, 0.15, len(sub))
            mcolor = PALETTE["msih"] if label == "MSI-H" else PALETTE["mss"]
            ax.scatter(i + jitter, sub["score"], c=mcolor, marker=marker,
                       alpha=0.6, s=25, edgecolors="white", linewidth=0.5, zorder=4)

    ax.axhline(0.5, color="#AAA", linestyle="--", linewidth=1, alpha=0.8)
    ax.set_xticks(positions)
    ax.set_xticklabels([f"Fold {f}" for f in folds], fontsize=11)
    ax.set_ylabel("MSI-H Prediction Score", fontweight="bold")
    ax.set_title("By Fold (◆=MSI-H, ●=MSS)", fontweight="bold")

    add_watermark(fig)
    fig.tight_layout(rect=[0, 0.02, 1, 0.94])
    save_fig(fig, out / "10_prediction_distributions.png")


# ═══════════════════════════════════════════════════════════════════════════
#  11. WATERFALL PLOT
# ═══════════════════════════════════════════════════════════════════════════

def plot_waterfall(results_dir: Path, out: Path):
    """Sorted prediction scores colored by true label."""
    preds_file = results_dir / "all_predictions.csv"
    if not preds_file.exists():
        print("  Skipping waterfall plot (no all_predictions.csv)")
        return

    df = pd.read_csv(preds_file).sort_values("score", ascending=False).reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(16, 6))
    fig.suptitle("Waterfall Plot — All Predictions Sorted by MSI-H Score",
                 fontweight="bold", fontsize=16)

    colors = [PALETTE["msih"] if s == "MSI-H" else PALETTE["mss"] for s in df["msi_status"]]
    ax.bar(range(len(df)), df["score"], color=colors, width=1.0,
           edgecolor="none", zorder=3)

    ax.axhline(0.5, color=PALETTE["text"], linewidth=1.5, linestyle="--",
               alpha=0.6, zorder=4, label="Decision threshold (0.5)")

    ax.set_xlabel("Sample (ranked by prediction score)", fontweight="bold")
    ax.set_ylabel("MSI-H Probability", fontweight="bold")
    ax.set_xlim(-0.5, len(df) - 0.5)
    ax.set_ylim(0, 1.02)

    legend_elements = [
        mpatches.Patch(facecolor=PALETTE["msih"], label="True MSI-H"),
        mpatches.Patch(facecolor=PALETTE["mss"], label="True MSS"),
        plt.Line2D([0], [0], color=PALETTE["text"], linestyle="--", label="Threshold"),
    ]
    ax.legend(handles=legend_elements, loc="upper right", fontsize=11)

    add_watermark(fig)
    fig.tight_layout(rect=[0, 0.02, 1, 0.94])
    save_fig(fig, out / "11_waterfall_plot.png")


# ═══════════════════════════════════════════════════════════════════════════
#  12. CALIBRATION CURVE
# ═══════════════════════════════════════════════════════════════════════════

def plot_calibration(results_dir: Path, out: Path):
    """Reliability diagram with histogram."""
    preds_file = results_dir / "all_predictions.csv"
    if not preds_file.exists() or not HAS_SKLEARN:
        print("  Skipping calibration curve")
        return

    df = pd.read_csv(preds_file)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10),
                                    gridspec_kw={"height_ratios": [3, 1]})
    fig.suptitle("Calibration Curve (Reliability Diagram)", fontweight="bold", fontsize=16)

    y_true = df["y_true"].values
    y_score = df["score"].values

    prob_true, prob_pred = calibration_curve(y_true, y_score, n_bins=10, strategy="uniform")

    # Calibration line
    ax1.plot(prob_pred, prob_true, "o-", color=PALETTE["accent2"], linewidth=2.5,
             markersize=8, label="Model", zorder=4)
    ax1.plot([0, 1], [0, 1], "--", color="#AAAAAA", linewidth=1.5, label="Perfectly calibrated")
    ax1.fill_between(prob_pred, prob_true, prob_pred, alpha=0.15, color=PALETTE["accent2"])

    ax1.set_xlabel("Mean Predicted Probability", fontweight="bold")
    ax1.set_ylabel("Fraction of Positives", fontweight="bold")
    ax1.set_xlim(-0.02, 1.02)
    ax1.set_ylim(-0.02, 1.02)
    ax1.legend(fontsize=11, loc="upper left")

    # Histogram
    ax2.hist(y_score[y_true == 0], bins=20, alpha=0.6, color=PALETTE["mss"],
             label="MSS", density=True)
    ax2.hist(y_score[y_true == 1], bins=20, alpha=0.6, color=PALETTE["msih"],
             label="MSI-H", density=True)
    ax2.set_xlabel("Predicted Probability", fontweight="bold")
    ax2.set_ylabel("Density", fontweight="bold")
    ax2.legend(fontsize=10)

    add_watermark(fig)
    fig.tight_layout(rect=[0, 0.02, 1, 0.94])
    save_fig(fig, out / "12_calibration_curve.png")


# ═══════════════════════════════════════════════════════════════════════════
#  13. TRAINING PERFORMANCE RADAR
# ═══════════════════════════════════════════════════════════════════════════

def plot_performance_radar(results_dir: Path, out: Path):
    """Radar/spider chart of per-fold metrics."""
    preds_file = results_dir / "all_predictions.csv"
    if not preds_file.exists() or not HAS_SKLEARN:
        print("  Skipping radar chart")
        return

    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

    df = pd.read_csv(preds_file)
    folds = sorted(df["fold"].unique())

    metrics = ["AUROC", "Accuracy", "F1", "Sensitivity", "Specificity"]
    n_metrics = len(metrics)

    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection="polar"))
    fig.suptitle("Performance Radar — Per-Fold Metrics", fontweight="bold", fontsize=16, y=0.98)

    angles = np.linspace(0, 2 * np.pi, n_metrics, endpoint=False).tolist()
    angles += angles[:1]

    for fold in folds:
        fold_data = df[df["fold"] == fold]
        y_true = fold_data["y_true"].values
        y_score = fold_data["score"].values
        y_pred = (y_score >= 0.5).astype(int)

        auroc = roc_auc_score(y_true, y_score) if len(np.unique(y_true)) > 1 else 0
        acc = accuracy_score(y_true, y_pred)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        sens = recall_score(y_true, y_pred, zero_division=0)
        spec = recall_score(1 - y_true, 1 - y_pred, zero_division=0)

        values = [auroc, acc, f1, sens, spec]
        values += values[:1]

        color = PALETTE["fold_colors"][(fold - 1) % 5]
        ax.plot(angles, values, "o-", linewidth=2, color=color,
                label=f"Fold {fold}", markersize=6)
        ax.fill(angles, values, alpha=0.1, color=color)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(metrics, fontsize=12, fontweight="bold")
    ax.set_ylim(0, 1.05)
    ax.set_rticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=10)

    add_watermark(fig)
    fig.tight_layout(rect=[0, 0.02, 1, 0.96])
    save_fig(fig, out / "13_performance_radar.png")


# ═══════════════════════════════════════════════════════════════════════════
#  14. SCORE HEATMAP (fold × patient)
# ═══════════════════════════════════════════════════════════════════════════

def plot_score_heatmap(results_dir: Path, out: Path):
    """Heatmap of prediction scores per patient if available."""
    preds_file = results_dir / "all_predictions.csv"
    if not preds_file.exists():
        print("  Skipping score heatmap (no all_predictions.csv)")
        return

    df = pd.read_csv(preds_file)
    if "patient" not in df.columns and "slide" not in df.columns:
        print("  Skipping score heatmap (no patient/slide column)")
        return

    id_col = "patient" if "patient" in df.columns else "slide"

    # Take top 30 samples by deviation from 0.5
    df["deviation"] = abs(df["score"] - 0.5)
    top = df.nlargest(min(40, len(df)), "deviation")

    fig, ax = plt.subplots(figsize=(14, 8))
    fig.suptitle("Prediction Score Heatmap — Most Confident Predictions",
                 fontweight="bold", fontsize=16)

    # Sort by score
    top = top.sort_values("score", ascending=False)
    patient_ids = [p[:15] for p in top[id_col].values]  # truncate long names

    cmap = LinearSegmentedColormap.from_list(
        "msicmap", [PALETTE["mss"], "#FFFFFF", PALETTE["msih"]]
    )

    scores = top["score"].values.reshape(1, -1)
    im = ax.imshow(scores, aspect="auto", cmap=cmap, vmin=0, vmax=1)

    for i, (score, true_label) in enumerate(zip(top["score"], top["msi_status"])):
        text_color = "white" if abs(score - 0.5) > 0.3 else PALETTE["text"]
        ax.text(i, 0, f"{score:.2f}", ha="center", va="center",
                fontsize=8, fontweight="bold", color=text_color)

    ax.set_xticks(range(len(patient_ids)))
    ax.set_xticklabels(patient_ids, rotation=90, fontsize=7)
    ax.set_yticks([])

    # Color bar
    cbar = fig.colorbar(im, ax=ax, orientation="horizontal", pad=0.15, aspect=40)
    cbar.set_label("MSI-H Probability", fontweight="bold")

    # True label markers
    for i, label in enumerate(top["msi_status"]):
        marker_color = PALETTE["msih"] if label == "MSI-H" else PALETTE["mss"]
        ax.plot(i, -0.4, "s", color=marker_color, markersize=6,
                clip_on=False, zorder=5)

    add_watermark(fig)
    fig.tight_layout(rect=[0, 0.02, 1, 0.94])
    save_fig(fig, out / "14_score_heatmap.png")


# ═══════════════════════════════════════════════════════════════════════════
#  15. SUMMARY DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════

def plot_summary_dashboard(df: pd.DataFrame, results_dir: Path, out: Path):
    """Multi-panel summary dashboard combining key metrics."""
    fig = plt.figure(figsize=(20, 14))
    fig.suptitle("MSI Classification Pipeline — Summary Dashboard",
                 fontweight="bold", fontsize=20, y=0.98)

    gs = gridspec.GridSpec(2, 3, hspace=0.35, wspace=0.3)

    # --- Panel 1: Cohort ---
    ax1 = fig.add_subplot(gs[0, 0])
    counts = df[["patient", "msi_status"]].drop_duplicates()["msi_status"].value_counts()
    msih = counts.get("MSI-H", 0)
    mss = counts.get("MSS", 0)
    ax1.pie([msih, mss], labels=["MSI-H", "MSS"],
            colors=[PALETTE["msih"], PALETTE["mss"]],
            autopct="%1.0f%%", startangle=90,
            wedgeprops=dict(width=0.45, edgecolor="white"),
            textprops=dict(fontsize=11, fontweight="bold"))
    ax1.set_title(f"Cohort (n={msih+mss})", fontweight="bold")

    # --- Panel 2: Fold distribution ---
    ax2 = fig.add_subplot(gs[0, 1])
    if "fold" in df.columns:
        patients = df[["patient", "msi_status", "fold"]].drop_duplicates()
        pivot = patients.pivot_table(index="fold", columns="msi_status", values="patient",
                                     aggfunc="count", fill_value=0)
        x = np.arange(len(pivot))
        w = 0.35
        if "MSI-H" in pivot.columns:
            ax2.bar(x - w/2, pivot["MSI-H"], w, color=PALETTE["msih"], label="MSI-H")
        if "MSS" in pivot.columns:
            ax2.bar(x + w/2, pivot["MSS"], w, color=PALETTE["mss"], label="MSS")
        ax2.set_xticks(x)
        ax2.set_xticklabels([f"F{i}" for i in pivot.index])
        ax2.legend(fontsize=9)
    ax2.set_title("Fold Balance", fontweight="bold")

    # --- Panel 3: AUROC bars ---
    ax3 = fig.add_subplot(gs[0, 2])
    auroc_file = results_dir / "cv_auroc_table.csv"
    if auroc_file.exists():
        adf = pd.read_csv(auroc_file)
        colors = [PALETTE["fold_colors"][i % 5] for i in range(len(adf))]
        ax3.bar(range(len(adf)), adf["auroc"], color=colors, edgecolor="white", width=0.6)
        mean = adf["auroc"].mean()
        ax3.axhline(mean, color=PALETTE["bg_dark"], linestyle="--", linewidth=2)
        ax3.set_xticks(range(len(adf)))
        ax3.set_xticklabels([f"F{int(f)}" for f in adf["fold"]])
        ax3.set_ylim(0, 1.05)
        ax3.text(0.95, 0.05, f"μ={mean:.3f}", transform=ax3.transAxes,
                 ha="right", fontweight="bold", fontsize=11)
    else:
        ax3.text(0.5, 0.5, "Awaiting\ntraining", transform=ax3.transAxes,
                 ha="center", va="center", fontsize=14, color="#AAA")
    ax3.set_title("Per-Fold AUROC", fontweight="bold")

    # --- Panel 4: ROC ---
    ax4 = fig.add_subplot(gs[1, 0])
    roc_file = results_dir / "roc_curves.csv"
    if roc_file.exists():
        roc_df = pd.read_csv(roc_file)
        mean_fpr = np.linspace(0, 1, 100)
        tprs = []
        for fold in sorted(roc_df["fold"].unique()):
            fd = roc_df[roc_df["fold"] == fold]
            color = PALETTE["fold_colors"][(fold-1) % 5]
            ax4.plot(fd["fpr"], fd["tpr"], color=color, alpha=0.5, linewidth=1)
            interp = np.interp(mean_fpr, fd["fpr"].values, fd["tpr"].values)
            interp[0] = 0.0
            tprs.append(interp)
        mean_tpr = np.mean(tprs, axis=0)
        mean_tpr[-1] = 1.0
        ax4.plot(mean_fpr, mean_tpr, color=PALETTE["bg_dark"], linewidth=2.5)
        ax4.plot([0, 1], [0, 1], "--", color="#CCC", linewidth=1)
    else:
        ax4.text(0.5, 0.5, "Awaiting\ntraining", transform=ax4.transAxes,
                 ha="center", va="center", fontsize=14, color="#AAA")
    ax4.set_title("ROC Curves", fontweight="bold")
    ax4.set_xlabel("FPR")
    ax4.set_ylabel("TPR")

    # --- Panel 5: Predictions ---
    ax5 = fig.add_subplot(gs[1, 1])
    preds_file = results_dir / "all_predictions.csv"
    if preds_file.exists():
        pdf = pd.read_csv(preds_file)
        for label, color in [("MSS", PALETTE["mss"]), ("MSI-H", PALETTE["msih"])]:
            vals = pdf.loc[pdf["msi_status"] == label, "score"]
            ax5.hist(vals, bins=20, alpha=0.6, color=color, label=label, density=True)
        ax5.axvline(0.5, color="#AAA", linestyle="--")
        ax5.legend(fontsize=9)
    else:
        ax5.text(0.5, 0.5, "Awaiting\ntraining", transform=ax5.transAxes,
                 ha="center", va="center", fontsize=14, color="#AAA")
    ax5.set_title("Score Distribution", fontweight="bold")
    ax5.set_xlabel("MSI-H Score")

    # --- Panel 6: Summary table ---
    ax6 = fig.add_subplot(gs[1, 2])
    ax6.axis("off")
    summary_file = results_dir / "cv_summary.json"
    if summary_file.exists():
        with open(summary_file) as f:
            summary = json.load(f)
        table_data = [
            ["Mean AUROC", f"{summary.get('mean_auroc', 0):.4f}"],
            ["SD AUROC", f"{summary.get('sd_auroc', 0):.4f}"],
            ["Mean AUPRC", f"{summary.get('mean_auprc', 0):.4f}"],
            ["Folds", str(summary.get("folds", "?"))],
            ["Total Samples", str(summary.get("total_samples", "?"))],
        ]
    else:
        table_data = [
            ["Status", "Pre-training"],
            ["Patients", str(len(df[["patient"]].drop_duplicates()))],
            ["Slides", str(len(df))],
            ["Folds", str(df["fold"].nunique()) if "fold" in df.columns else "?"],
        ]

    table = ax6.table(cellText=table_data, colLabels=["Metric", "Value"],
                      loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.0, 1.8)
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor("#E0E0E0")
        if row == 0:
            cell.set_facecolor(PALETTE["bg_dark"])
            cell.set_text_props(color="white", fontweight="bold")
        elif row % 2 == 0:
            cell.set_facecolor("#F0F4FF")
    ax6.set_title("Results Summary", fontweight="bold")

    add_watermark(fig)
    save_fig(fig, out / "15_summary_dashboard.png")


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN ENTRY
# ═══════════════════════════════════════════════════════════════════════════

def generate_all_visualizations(project_dir: Path, output_dir: Path):
    """Generate all visualizations."""
    print("\n" + "=" * 70)
    print("GENERATING ADVANCED VISUALIZATIONS")
    print("=" * 70)

    setup_style()

    annotations = project_dir / "annotations" / "tcga_crc_msi_annotations.csv"
    if not annotations.exists():
        print(f"ERROR: Missing annotations at {annotations}")
        return

    df = pd.read_csv(annotations)
    figures_dir = output_dir / "figures"
    results_dir = output_dir / "results"
    figures_dir.mkdir(parents=True, exist_ok=True)

    # Also check slideflow_project/results if output/results doesn't exist
    if not results_dir.exists() or not any(results_dir.glob("*.csv")):
        alt_results = project_dir / "slideflow_project" / "results"
        if alt_results.exists():
            results_dir = alt_results

    print(f"\nAnnotations: {len(df)} rows")
    print(f"Figures output: {figures_dir}")
    print(f"Results source: {results_dir}\n")

    # --- Cohort analysis (always available) ---
    print("Generating cohort analysis figures...")
    plot_cohort_overview(df, figures_dir)
    plot_fold_distribution(df, figures_dir)
    plot_site_distribution(df, figures_dir)
    plot_msi_scores(df, figures_dir)
    plot_project_distribution(df, figures_dir)

    # --- Training results (only after training) ---
    print("\nGenerating training result figures...")
    plot_roc_curves(results_dir, figures_dir)
    plot_auroc_bar(results_dir, figures_dir)
    plot_pr_curves(results_dir, figures_dir)
    plot_confusion_matrices(results_dir, figures_dir)
    plot_prediction_distributions(results_dir, figures_dir)
    plot_waterfall(results_dir, figures_dir)
    plot_calibration(results_dir, figures_dir)
    plot_performance_radar(results_dir, figures_dir)
    plot_score_heatmap(results_dir, figures_dir)

    # --- Dashboard ---
    print("\nGenerating summary dashboard...")
    plot_summary_dashboard(df, results_dir, figures_dir)

    # Generate figure index
    figures = sorted(figures_dir.glob("*.png"))
    index = {
        "total_figures": len(figures),
        "figures": [{"name": f.stem, "file": f.name} for f in figures],
    }
    (figures_dir / "figure_index.json").write_text(
        json.dumps(index, indent=2), encoding="utf-8"
    )

    print(f"\n{'=' * 70}")
    print(f"VISUALIZATION COMPLETE: {len(figures)} figures generated")
    print(f"Output directory: {figures_dir}")
    print(f"{'=' * 70}")


# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate advanced visualizations")
    parser.add_argument("--project-dir", type=str, default=None,
                        help="Path to project root")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Path to output directory")
    args = parser.parse_args()

    if args.project_dir:
        project_dir = Path(args.project_dir)
    else:
        project_dir = Path(__file__).resolve().parents[1]

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = project_dir / "output"

    generate_all_visualizations(project_dir, output_dir)
