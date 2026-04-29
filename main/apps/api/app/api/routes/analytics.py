from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.approach_2.database import models as approach2_models
from app.approach_2.database.setup import SessionLocal
from app.approach_2.services.experiment_labels import classify_experiment
from app.api.routes.parallel_pipeline import (
    ParallelMetric,
    ParallelSourceStatus,
    build_parallel_metrics,
    collect_parallel_records,
)
from app.models.monte_carlo import StableBestCandidate
from app.models.monte_carlo import StableBestRequest
from app.services.monte_carlo import MonteCarloService
from app.services.vm import VmService

router = APIRouter()


class Approach1Snapshot(BaseModel):
    trial_id: str = ""
    status: str = "idle"
    step: str = "pending"
    running: bool = False
    slide_backend: str = "unknown"
    error: str = ""
    slides_total: int = 0
    tfrecord_files: int = 0
    unfinished_files: int = 0
    bag_files: int = 0
    tfrecord_bytes: int = 0
    bag_bytes: int = 0
    log_excerpt: str = ""


class Approach2Snapshot(BaseModel):
    runs_total: int = 0
    completed_runs: int = 0
    latest_experiment_id: str = ""
    latest_name: str = ""
    latest_status: str = "idle"
    latest_metrics: dict[str, Any] = {}
    history: list[dict[str, Any]] = []
    class_distribution: dict[str, int] = {}


class MonteCarloSnapshot(BaseModel):
    stable_best: StableBestCandidate | None = None
    total_candidates: int = 0
    mc_result_trials: int = 0
    dropout_ready: int = 0
    bootstrap_ready: int = 0


class DashboardAnalyticsResponse(BaseModel):
    approach1: Approach1Snapshot
    approach2: Approach2Snapshot
    monte_carlo: MonteCarloSnapshot
    comparison_metrics: list[ParallelMetric]
    comparison_sources: list[ParallelSourceStatus]


@router.get("/dashboard", response_model=DashboardAnalyticsResponse)
def dashboard() -> DashboardAnalyticsResponse:
    approach1 = _collect_approach1_snapshot()
    approach2 = _collect_approach2_snapshot()
    monte_carlo = _collect_monte_carlo_snapshot()
    records, sources = collect_parallel_records()
    comparison_metrics = build_parallel_metrics(records)

    return DashboardAnalyticsResponse(
        approach1=approach1,
        approach2=approach2,
        monte_carlo=monte_carlo,
        comparison_metrics=comparison_metrics,
        comparison_sources=sources,
    )


def _collect_approach1_snapshot() -> Approach1Snapshot:
    command = r"""
python3 - <<'PY'
import json
import re
import subprocess
from pathlib import Path

status_dir = Path("automation/status")
logs_dir = Path("automation/logs")
slides_dir = Path("slideflow_project/data/slides")
tfrecord_root = Path("slideflow_project/tfrecords")
bags_root = Path("slideflow_project/bags")

rows = []
for path in sorted(status_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
    try:
        rows.append((path, json.loads(path.read_text())))
    except Exception:
        continue

running_trial = ""
ps_lines = subprocess.run(
    ["ps", "-eo", "args"], capture_output=True, text=True, check=False
).stdout.splitlines()
for line in ps_lines:
    if "run_n8n_msi_trial.py" in line and "--trial-json" in line:
        match = re.search(r"automation/trials/([^/]+)/trial\.json", line)
        if match:
            running_trial = match.group(1)
            break

status_data = {}
trial_id = running_trial
if running_trial:
    for _, data in rows:
        if data.get("trial_id") == running_trial:
            status_data = data
            break
if not status_data and rows:
    path, data = rows[0]
    trial_id = str(data.get("trial_id", path.stem))
    status_data = data

log_excerpt = ""
slide_backend = "unknown"
if trial_id:
    log_path = logs_dir / f"{trial_id}.log"
    if log_path.exists():
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
        log_excerpt = "\n".join(log_text.splitlines()[-25:])
        patterns = [
            r"slide_backend=([A-Za-z0-9_.-]+)",
            r"Slide reading backend:\s+([A-Za-z0-9_.-]+)",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, log_text)
            if matches:
                slide_backend = matches[-1]
                break

tfrecord_files = list(tfrecord_root.rglob("*.tfrecords")) if tfrecord_root.exists() else []
unfinished_files = list(tfrecord_root.rglob("*.unfinished")) if tfrecord_root.exists() else []
bag_files = [p for p in bags_root.rglob("*") if p.is_file()] if bags_root.exists() else []
slide_files = list(slides_dir.glob("*.svs")) + list(slides_dir.glob("*.ndpi")) if slides_dir.exists() else []

payload = {
    "trial_id": trial_id,
    "status": status_data.get("state", "idle"),
    "step": status_data.get("step", "pending"),
    "running": bool(running_trial),
    "slide_backend": slide_backend,
    "error": status_data.get("error", ""),
    "slides_total": len(slide_files),
    "tfrecord_files": len(tfrecord_files),
    "unfinished_files": len(unfinished_files),
    "bag_files": len(bag_files),
    "tfrecord_bytes": sum(p.stat().st_size for p in tfrecord_files),
    "bag_bytes": sum(p.stat().st_size for p in bag_files),
    "log_excerpt": log_excerpt,
}
print(json.dumps(payload))
PY
"""
    result = VmService().run_project_command("approach1Analytics", command, timeout=60)
    try:
        return Approach1Snapshot(**json.loads(result.stdout))
    except Exception:
        return Approach1Snapshot(error=result.stderr or result.stdout or "Unable to read Approach 1 snapshot.")


def _collect_approach2_snapshot() -> Approach2Snapshot:
    session = SessionLocal()
    try:
        experiments = [
            experiment
            for experiment in session.query(approach2_models.Experiment)
            .order_by(approach2_models.Experiment.id.desc())
            .all()
            if classify_experiment(
                name=experiment.name,
                model_type=experiment.model_type,
                parameters=experiment.parameters if isinstance(experiment.parameters, dict) else None,
                metrics=experiment.metrics if isinstance(experiment.metrics, dict) else None,
            )
            == "Approach2"
        ]
    finally:
        session.close()

    latest = experiments[0] if experiments else None
    latest_metrics = latest.metrics if latest and isinstance(latest.metrics, dict) else {}
    history = latest_metrics.get("history", []) if isinstance(latest_metrics, dict) else []
    class_distribution = latest_metrics.get("class_distribution", {}) if isinstance(latest_metrics, dict) else {}

    return Approach2Snapshot(
        runs_total=len(experiments),
        completed_runs=sum(1 for exp in experiments if exp.status == "completed"),
        latest_experiment_id=latest.experiment_id if latest else "",
        latest_name=latest.name if latest else "",
        latest_status=latest.status if latest else "idle",
        latest_metrics=latest_metrics if isinstance(latest_metrics, dict) else {},
        history=history if isinstance(history, list) else [],
        class_distribution=class_distribution if isinstance(class_distribution, dict) else {},
    )


def _collect_monte_carlo_snapshot() -> MonteCarloSnapshot:
    service = MonteCarloService()
    stable_best = service.stable_best(StableBestRequest())
    local_best = None
    local_total = 0

    session = SessionLocal()
    try:
        local_mc = [
            experiment
            for experiment in session.query(approach2_models.Experiment)
            .filter(approach2_models.Experiment.status == "completed")
            .all()
            if classify_experiment(
                name=experiment.name,
                model_type=experiment.model_type,
                parameters=experiment.parameters if isinstance(experiment.parameters, dict) else None,
                metrics=experiment.metrics if isinstance(experiment.metrics, dict) else None,
            )
            == "MonteCarlo"
            and isinstance(experiment.metrics, dict)
        ]
    finally:
        session.close()

    local_total = len(local_mc)
    if local_mc and stable_best.best is None:
        scored: list[StableBestCandidate] = []
        for experiment in local_mc:
            metrics = experiment.metrics if isinstance(experiment.metrics, dict) else {}
            params = experiment.parameters if isinstance(experiment.parameters, dict) else {}
            scored.append(
                StableBestCandidate(
                    trial_id=experiment.experiment_id,
                    mean_auroc=float(metrics.get("val_auroc_ovr_macro") or 0.0),
                    sd_auroc=0.0,
                    mean_auprc=float(metrics.get("mean_auprc") or 0.0),
                    sd_auprc=0.0,
                    balanced_accuracy=float(metrics.get("best_val_accuracy") or metrics.get("accuracy") or 0.0),
                    msi_h_sensitivity=float(metrics.get("msi_h_sensitivity") or 0.0),
                    calibration_score=float(metrics.get("calibration_score") or 0.0),
                    seed_std=0.0,
                    stability_score=float(metrics.get("val_auroc_ovr_macro") or metrics.get("best_val_accuracy") or 0.0),
                    folds_completed=1,
                    feature_extractor=str(metrics.get("backbone") or ""),
                    mil_model=str(experiment.model_type or ""),
                    epochs=int(metrics.get("epochs") or 0),
                    seed=int(metrics.get("seed") or params.get("seed") or 0),
                )
            )
        scored.sort(key=lambda item: item.stability_score, reverse=True)
        local_best = scored[0]

    command = r"""
python3 - <<'PY'
import json
from pathlib import Path

mc_root = Path("automation/mc_results")
trial_dirs = [p for p in mc_root.iterdir() if p.is_dir()] if mc_root.exists() else []
dropout_ready = sum(1 for p in trial_dirs if (p / "mc_dropout.json").exists())
bootstrap_ready = sum(1 for p in trial_dirs if (p / "bootstrap_ci.json").exists())
print(json.dumps({
    "mc_result_trials": len(trial_dirs),
    "dropout_ready": dropout_ready,
    "bootstrap_ready": bootstrap_ready,
}))
PY
"""
    result = VmService().run_project_command("monteCarloAnalytics", command, timeout=45)
    try:
        remote = json.loads(result.stdout)
    except Exception:
        remote = {"mc_result_trials": 0, "dropout_ready": 0, "bootstrap_ready": 0}

    return MonteCarloSnapshot(
        stable_best=stable_best.best or local_best,
        total_candidates=stable_best.total_evaluated or local_total,
        mc_result_trials=int(remote.get("mc_result_trials", 0)),
        dropout_ready=int(remote.get("dropout_ready", 0)),
        bootstrap_ready=int(remote.get("bootstrap_ready", 0)),
    )
