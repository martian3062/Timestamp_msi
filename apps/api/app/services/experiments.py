from __future__ import annotations

import hashlib
import itertools
import json

from app.models.experiments import (
    BestExperimentResponse,
    ExperimentActionResponse,
    ExperimentGridRequest,
    ExperimentMetric,
    ExperimentPlanResponse,
    ExperimentRunRequest,
    ExperimentStatusResponse,
    ExperimentTrial,
)
from app.services.vm import VmService


RUNNER_SCRIPT = r'''"""n8n-triggered Slideflow MSI trial runner.

This runner writes only real status and metrics collected from Slideflow output.
It does not synthesize scores when prediction files are missing.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import traceback
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)


PROJECT_DIR = Path(__file__).resolve().parents[1]
SF_ROOT = PROJECT_DIR / "slideflow_project"
ANNOTATIONS = PROJECT_DIR / "annotations" / "tcga_crc_msi_annotations.csv"
SLIDES_DIR = SF_ROOT / "data" / "slides"
RESULTS_ROOT = PROJECT_DIR / "automation" / "results"
STATUS_ROOT = PROJECT_DIR / "automation" / "status"

OUTCOME = "msi_status"
POS_LABEL = "MSI-H"
NEG_LABEL = "MSS"
TILE_PX = 256
TILE_UM = 128


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def status_path(trial_id: str) -> Path:
    return STATUS_ROOT / f"{safe_name(trial_id)}.json"


def result_dir(trial_id: str) -> Path:
    return RESULTS_ROOT / safe_name(trial_id)


def update_status(trial: dict, state: str, **extra) -> None:
    payload = {
        "trial_id": trial["trial_id"],
        "state": state,
        "feature_extractor": trial["feature_extractor"],
        "mil_model": trial["mil_model"],
        "learning_rate": trial["learning_rate"],
        "epochs": trial["epochs"],
        "seed": trial["seed"],
        "folds": trial["folds"],
        **extra,
    }
    write_json(status_path(trial["trial_id"]), payload)


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
        raise ValueError(f"Unexpected MSI labels: {bad}")
    return df


def import_slideflow():
    import slideflow as sf

    for backend in ("cucim", "opencv"):
        try:
            sf.set_backend(backend)
            print(f"Using Slideflow backend: {backend}", flush=True)
            break
        except Exception as exc:
            print(f"Could not set backend {backend}: {exc}", flush=True)
    return sf


def load_project():
    sf = import_slideflow()
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
    return sf, project


def make_dataset(project):
    return project.dataset(
        tile_px=TILE_PX,
        tile_um=TILE_UM,
        filter_blank=OUTCOME,
        verification="both",
    )


def build_extractor(sf, extractor_name: str):
    return sf.build_feature_extractor(
        extractor_name,
        tile_px=TILE_PX,
        resize=True,
        mixed_precision=True,
    )


def mil_tools(sf):
    if hasattr(sf, "mil"):
        return sf.mil
    if hasattr(sf, "model") and hasattr(sf.model, "mil"):
        return sf.model.mil
    import slideflow.mil as mil

    return mil


def split_dataset(dataset, fold: int):
    params = {
        "model_type": "classification",
        "labels": OUTCOME,
        "val_strategy": "k-fold-manual",
        "k_fold_iter": fold,
        "splits": str(SF_ROOT / "splits.json"),
    }
    try:
        return dataset.split(**params, k_fold_header="fold")
    except TypeError:
        return dataset.split(**params, val_k_fold_header="fold")


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
    for column in preferred:
        if column in df.columns and pd.api.types.is_numeric_dtype(df[column]):
            return column
    numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    raise ValueError(f"Could not infer positive-class score column: {numeric}")


def aggregate_trial(trial: dict) -> dict:
    trial_id = trial["trial_id"]
    out_dir = result_dir(trial_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    prediction_files = sorted(
        p
        for p in list(SF_ROOT.glob("**/*pred*.parquet"))
        + list(SF_ROOT.glob("**/*pred*.csv"))
        if trial_id in str(p)
    )
    if not prediction_files:
        raise FileNotFoundError(
            f"No prediction files found for trial {trial_id}. Training may have failed."
        )

    rows = []
    roc_rows = []
    pr_rows = []
    confusion = []
    for path in prediction_files:
        df = read_table(path)
        if OUTCOME not in df.columns:
            continue
        score_col = infer_score_column(df)
        y_true = (df[OUTCOME] == POS_LABEL).astype(int).to_numpy()
        y_score = df[score_col].to_numpy()
        if len(np.unique(y_true)) < 2:
            continue
        fold_match = re.search(r"fold_(\d+)", str(path))
        fold = int(fold_match.group(1)) if fold_match else len(rows) + 1
        fpr, tpr, _ = roc_curve(y_true, y_score)
        precision, recall, _ = precision_recall_curve(y_true, y_score)
        y_pred = (y_score >= 0.5).astype(int)
        rows.append(
            {
                "trial_id": trial_id,
                "fold": fold,
                "n": int(len(df)),
                "score_column": score_col,
                "auroc": float(roc_auc_score(y_true, y_score)),
                "auprc": float(average_precision_score(y_true, y_score)),
                "file": str(path),
            }
        )
        roc_rows.append(pd.DataFrame({"fold": fold, "fpr": fpr, "tpr": tpr}))
        pr_rows.append(pd.DataFrame({"fold": fold, "precision": precision, "recall": recall}))
        confusion.append({"fold": fold, "matrix": confusion_matrix(y_true, y_pred).tolist()})

    if not rows:
        raise FileNotFoundError(f"No usable prediction tables found for trial {trial_id}.")

    table = pd.DataFrame(rows).sort_values("fold")
    table.to_csv(out_dir / "fold_metrics.csv", index=False)
    if roc_rows:
        pd.concat(roc_rows).to_csv(out_dir / "roc_curves.csv", index=False)
    if pr_rows:
        pd.concat(pr_rows).to_csv(out_dir / "pr_curves.csv", index=False)

    metrics = {
        **trial,
        "mean_auroc": float(table["auroc"].mean()),
        "sd_auroc": float(table["auroc"].std(ddof=1)),
        "mean_auprc": float(table["auprc"].mean()),
        "sd_auprc": float(table["auprc"].std(ddof=1)),
        "folds_completed": int(len(table)),
        "total_samples": int(table["n"].sum()),
        "confusion_matrices": confusion,
    }
    write_json(out_dir / "metrics.json", metrics)
    return metrics


def run_trial(config_path: Path) -> None:
    trial = json.loads(config_path.read_text(encoding="utf-8"))
    random.seed(int(trial["seed"]))
    np.random.seed(int(trial["seed"]))
    try:
        import torch

        torch.manual_seed(int(trial["seed"]))
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(int(trial["seed"]))
    except Exception as exc:
        print(f"Torch seeding skipped: {exc}", flush=True)

    update_status(trial, "running", step="validating_inputs")
    df = require_inputs()
    print(df[[OUTCOME, "patient"]].drop_duplicates()[OUTCOME].value_counts(), flush=True)

    sf, project = load_project()
    dataset = make_dataset(project)
    extractor_name = trial["feature_extractor"]
    bags_dir = SF_ROOT / "bags" / f"{safe_name(extractor_name)}_{TILE_PX}px_{TILE_UM}um"

    if not bags_dir.exists() or not any(bags_dir.iterdir()):
        update_status(trial, "running", step="generating_feature_bags")
        extractor = build_extractor(sf, extractor_name)
        bags_dir.mkdir(parents=True, exist_ok=True)
        project.generate_feature_bags(extractor, dataset, outdir=str(bags_dir))
    else:
        print(f"Reusing existing bags: {bags_dir}", flush=True)

    update_status(trial, "running", step="training")
    config = mil_tools(sf).mil_config(
        trial["mil_model"],
        lr=float(trial["learning_rate"]),
        epochs=int(trial["epochs"]),
    )
    for fold in trial["folds"]:
        fold = int(fold)
        print(f"Training trial={trial['trial_id']} fold={fold}", flush=True)
        train_ds, val_ds = split_dataset(dataset, fold)
        project.train_mil(
            config=config,
            train_dataset=train_ds,
            val_dataset=val_ds,
            outcomes=OUTCOME,
            bags=str(bags_dir),
            exp_label=f"n8n_{trial['trial_id']}_{safe_name(trial['mil_model'])}_fold_{fold}",
            attention_heatmaps=True,
            cmap="magma",
            interpolation=None,
        )

    update_status(trial, "running", step="aggregating")
    metrics = aggregate_trial(trial)
    update_status(trial, "completed", step="done", metrics_path=str(result_dir(trial["trial_id"]) / "metrics.json"))
    print(json.dumps(metrics, indent=2, sort_keys=True), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trial-json", required=True)
    args = parser.parse_args()
    config_path = Path(args.trial_json)
    trial = json.loads(config_path.read_text(encoding="utf-8"))
    try:
        run_trial(config_path)
    except Exception as exc:
        update_status(
            trial,
            "failed",
            step="error",
            error=str(exc),
            traceback=traceback.format_exc(),
        )
        raise


if __name__ == "__main__":
    main()
'''


class ExperimentService:
    def __init__(self, vm: VmService | None = None) -> None:
        self.vm = vm or VmService()

    def build_plan(self, request: ExperimentGridRequest) -> ExperimentPlanResponse:
        trials: list[ExperimentTrial] = []
        product = itertools.product(
            request.feature_extractors,
            request.mil_models,
            request.learning_rates,
            request.epochs,
            request.seeds,
        )
        for extractor, model, lr, epochs, seed in product:
            trial_key = json.dumps(
                {
                    "feature_extractor": extractor,
                    "mil_model": model,
                    "learning_rate": lr,
                    "epochs": epochs,
                    "seed": seed,
                    "folds": request.folds,
                },
                sort_keys=True,
            )
            digest = hashlib.sha1(trial_key.encode("utf-8")).hexdigest()[:10]
            trials.append(
                ExperimentTrial(
                    trial_id=f"trial_{digest}",
                    feature_extractor=extractor,
                    mil_model=model,
                    learning_rate=lr,
                    epochs=epochs,
                    seed=seed,
                    folds=request.folds,
                    primary_metric=request.primary_metric,
                    metric_direction=request.metric_direction,
                )
            )
            if len(trials) >= request.max_trials:
                break

        return ExperimentPlanResponse(
            trial_count=len(trials),
            primary_metric=request.primary_metric,
            metric_direction=request.metric_direction,
            trials=trials,
        )

    def bootstrap(self) -> ExperimentActionResponse:
        result = self.vm.write_project_file(
            "scripts/run_n8n_msi_trial.py",
            RUNNER_SCRIPT,
            action="bootstrapExperimentRunner",
            mode="755",
        )
        return ExperimentActionResponse(action=result.action, stdout=result.stdout, stderr=result.stderr)

    def start_trial(self, request: ExperimentRunRequest) -> ExperimentActionResponse:
        trial = request.trial
        trial_json = trial.model_dump_json(indent=2)
        config_path = f"automation/trials/{trial.trial_id}/trial.json"
        write_result = self.vm.write_project_file(
            config_path,
            trial_json,
            action="writeTrialConfig",
        )
        if not write_result.ok:
            return ExperimentActionResponse(
                ok=False,
                action="startExperimentTrial",
                trial_id=trial.trial_id,
                stdout=write_result.stdout,
                stderr=write_result.stderr,
            )

        command = (
            "mkdir -p automation/logs automation/status automation/results "
            f"&& nohup pathology310-run python scripts/run_n8n_msi_trial.py "
            f"--trial-json {self.vm.project_path(config_path)!r} "
            f"> automation/logs/{trial.trial_id}.log 2>&1 & "
            f"echo started {trial.trial_id}"
        )
        result = self.vm.run_project_command("startExperimentTrial", command)
        return ExperimentActionResponse(
            ok=result.ok,
            action=result.action,
            trial_id=trial.trial_id,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    def status(self, trial_id: str) -> ExperimentStatusResponse:
        safe_trial_id = self._safe_token(trial_id)
        command = f"""
RUNNING=0
if ps -eo args | grep -F 'run_n8n_msi_trial.py' | grep -F '{safe_trial_id}' | grep -v grep >/dev/null 2>&1; then
  RUNNING=1
fi
echo "__RUNNING__${{RUNNING}}"
echo "__STATUS__"
cat automation/status/{safe_trial_id}.json 2>/dev/null || true
echo
echo "__METRICS__"
cat automation/results/{safe_trial_id}/metrics.json 2>/dev/null || true
echo
echo "__LOG__"
tail -n 80 automation/logs/{safe_trial_id}.log 2>/dev/null || true
"""
        result = self.vm.run_project_command("experimentStatus", command)
        sections = self._split_status(result.stdout)
        return ExperimentStatusResponse(
            ok=result.ok,
            action=result.action,
            trial_id=safe_trial_id,
            stdout=result.stdout,
            stderr=result.stderr,
            running=sections["running"],
            status_json=sections["status_json"],
            metrics_json=sections["metrics_json"],
            log_tail=sections["log_tail"],
        )

    def best(self, primary_metric: str, metric_direction: str) -> BestExperimentResponse:
        metric = self._safe_token(primary_metric)
        direction = "min" if metric_direction == "min" else "max"
        command = f"""
python3 - <<'PY'
import json
from pathlib import Path
metric = {metric!r}
direction = {direction!r}
rows = []
for path in Path("automation/results").glob("*/metrics.json"):
    try:
        data = json.loads(path.read_text())
    except Exception:
        continue
    value = data.get(metric)
    if isinstance(value, (int, float)):
        rows.append({{"trial_id": data.get("trial_id", path.parent.name), "metric": metric, "value": float(value), "metrics": data}})
rows.sort(key=lambda item: item["value"], reverse=(direction == "max"))
print(json.dumps({{"rows": rows, "best": rows[0] if rows else None}}))
PY
"""
        result = self.vm.run_project_command("bestExperiment", command)
        payload = json.loads(result.stdout or '{"rows": [], "best": null}')
        best = payload.get("best")
        return BestExperimentResponse(
            primary_metric=metric,
            metric_direction=direction,
            best=ExperimentMetric(**best) if best else None,
            completed_trials=len(payload.get("rows", [])),
        )

    @staticmethod
    def _safe_token(value: str) -> str:
        return "".join(char for char in value if char.isalnum() or char in "_.-")

    @staticmethod
    def _split_status(stdout: str) -> dict:
        running = "__RUNNING__1" in stdout

        def between(start: str, end: str | None) -> str:
            if start not in stdout:
                return ""
            after = stdout.split(start, 1)[1]
            if end and end in after:
                return after.split(end, 1)[0].strip()
            return after.strip()

        status_text = between("__STATUS__", "__METRICS__")
        metrics_text = between("__METRICS__", "__LOG__")
        log_tail = between("__LOG__", None)

        def parse_json(value: str) -> dict | None:
            if not value:
                return None
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None

        return {
            "running": running,
            "status_json": parse_json(status_text),
            "metrics_json": parse_json(metrics_text),
            "log_tail": log_tail,
        }
