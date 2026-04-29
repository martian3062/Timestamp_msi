from __future__ import annotations

import json
import math
import statistics
import uuid
from typing import Any, Literal

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app.approach_2.database import models
from app.approach_2.database.setup import SessionLocal
from app.approach_2.services.experiment_labels import classify_experiment
from app.services.vm import VmService

router = APIRouter()


METRIC_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Accuracy", ("best_val_accuracy", "val_accuracy", "accuracy")),
    ("AUROC", ("val_auroc_ovr_macro", "mean_auroc", "auroc", "auc", "roc_auc", "val_auroc")),
    ("AUPRC", ("mean_auprc", "auprc", "average_precision", "val_auprc")),
    ("F1 Score", ("final_val_f1_macro", "f1", "f1_score", "mean_f1", "val_f1", "val_f1_macro")),
    ("Sensitivity", ("msi_h_sensitivity", "sensitivity", "recall", "val_recall")),
    ("Specificity", ("specificity", "val_specificity")),
    ("Balanced Accuracy", ("balanced_accuracy", "balanced_acc", "val_balanced_accuracy")),
    ("Stable Score", ("stability_score", "stable_score")),
)

SCORE_ALIASES: tuple[tuple[str, ...], ...] = (
    ("stability_score", "stable_score"),
    ("val_auroc_ovr_macro", "mean_auroc", "auroc", "auc", "roc_auc", "val_auroc"),
    ("best_val_accuracy", "val_accuracy", "accuracy"),
    ("mean_auprc", "auprc", "average_precision", "val_auprc"),
)


class ParallelMetric(BaseModel):
    name: str
    Approach1: float | None = None
    Approach2: float | None = None
    MonteCarlo: float | None = None


class ParallelSourceStatus(BaseModel):
    name: Literal["Approach1", "Approach2", "MonteCarlo"]
    ok: bool
    source: str
    message: str = ""
    records_found: int = 0


class ParallelStartResponse(BaseModel):
    ok: bool
    execution_id: str
    status: Literal["pending", "running", "completed", "failed"]
    message: str


class ParallelMetricsResponse(BaseModel):
    ok: bool
    execution_id: str
    status: Literal["pending", "running", "completed", "failed"]
    message: str
    metrics: list[ParallelMetric]
    sources: list[ParallelSourceStatus]


executions_store: dict[str, dict[str, Any]] = {}


def execute_parallel_pipelines(execution_id: str) -> None:
    executions_store[execution_id]["status"] = "running"
    try:
        records, sources = collect_parallel_records()
        metrics = build_parallel_metrics(records)
        if metrics:
            message = "Loaded real completed metrics from available VM and platform artifacts."
        else:
            message = "No completed metric artifacts were found yet. Run a training job first."

        executions_store[execution_id].update(
            status="completed",
            message=message,
            metrics=metrics,
            sources=sources,
        )
    except Exception as exc:  # pragma: no cover - defensive boundary for background work
        executions_store[execution_id].update(
            status="failed",
            message=str(exc),
            metrics=[],
            sources=[],
        )


@router.post("/start", response_model=ParallelStartResponse)
def start_parallel_pipeline(background_tasks: BackgroundTasks) -> ParallelStartResponse:
    execution_id = str(uuid.uuid4())
    executions_store[execution_id] = {
        "status": "pending",
        "message": "Parallel metrics snapshot queued.",
        "metrics": [],
        "sources": [],
    }
    background_tasks.add_task(execute_parallel_pipelines, execution_id)

    return ParallelStartResponse(
        ok=True,
        execution_id=execution_id,
        status="pending",
        message="Parallel metrics snapshot queued. Only completed artifact metrics are reported.",
    )


@router.get("/metrics/{execution_id}", response_model=ParallelMetricsResponse)
def get_parallel_metrics(execution_id: str) -> ParallelMetricsResponse:
    execution = executions_store.get(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution ID not found")

    return ParallelMetricsResponse(
        ok=execution["status"] != "failed",
        execution_id=execution_id,
        status=execution["status"],
        message=execution.get("message", ""),
        metrics=execution.get("metrics", []),
        sources=execution.get("sources", []),
    )


def collect_parallel_records() -> tuple[dict[str, list[dict[str, Any]]], list[ParallelSourceStatus]]:
    records: dict[str, list[dict[str, Any]]] = {
        "Approach1": [],
        "Approach2": [],
        "MonteCarlo": [],
    }
    sources: list[ParallelSourceStatus] = []

    sql_rows, sql_counts = _collect_sql_metric_rows()
    for row in sql_rows:
        label = row.get("approach_label", "Approach2")
        if label in records:
            records[label].append(row)

    if all(sql_counts.get(label, 0) > 0 for label in records):
        return records, [
            ParallelSourceStatus(
                name=label,
                ok=True,
                source="SQL experiments.metrics",
                records_found=sql_counts.get(label, 0),
            )
            for label in ("Approach1", "Approach2", "MonteCarlo")
        ]

    vm_rows, vm_status = _collect_vm_metric_rows()
    sources.extend(vm_status)
    for row in vm_rows:
        label = _classify_vm_record(row)
        records[label].append(row)

    vm_counts = {source.name: source.records_found for source in sources}
    sources = [
        ParallelSourceStatus(
            name=label,
            ok=True,
            source="VM automation/results + output/triad_runs + SQL experiments.metrics",
            records_found=vm_counts.get(label, 0) + sql_counts.get(label, 0),
        )
        for label in ("Approach1", "Approach2", "MonteCarlo")
    ]

    return records, sources


def build_parallel_metrics(records: dict[str, list[dict[str, Any]]]) -> list[ParallelMetric]:
    selected = {
        name: _select_record_for_label(name, rows)
        for name, rows in records.items()
    }

    metric_rows: list[ParallelMetric] = []
    for display_name, aliases in METRIC_ALIASES:
        row = ParallelMetric(
            name=display_name,
            Approach1=_metric_value(_record_metrics(selected["Approach1"]), aliases),
            Approach2=_metric_value(_record_metrics(selected["Approach2"]), aliases),
            MonteCarlo=_metric_value(_record_metrics(selected["MonteCarlo"]), aliases),
        )
        if row.Approach1 is not None or row.Approach2 is not None or row.MonteCarlo is not None:
            metric_rows.append(row)

    return metric_rows


def _collect_vm_metric_rows() -> tuple[list[dict[str, Any]], list[ParallelSourceStatus]]:
    command = r"""
python3 - <<'PY'
import json
from pathlib import Path

rows = []
roots = [
    Path("automation/results"),
    Path("output/triad_runs"),
]

for root in roots:
    for path in sorted(root.glob("*/metrics.json")):
        try:
            data = json.loads(path.read_text())
        except Exception:
            continue
        rows.append({
            "trial_id": data.get("trial_id", path.parent.name),
            "path": str(path),
            "metrics": data,
            "created_at": path.stat().st_mtime,
        })

print(json.dumps({"rows": rows}))
PY
"""
    result = VmService().run_project_command("parallelMetricsSnapshot", command, timeout=45)
    if not result.ok:
        message = result.stderr or result.stdout or "VM metric scan failed."
        status = [
            ParallelSourceStatus(
                name="Approach1",
                ok=False,
                source="VM automation/results/*/metrics.json + output/triad_runs/*/metrics.json",
                message=message,
            ),
            ParallelSourceStatus(
                name="Approach2",
                ok=False,
                source="VM automation/results/*/metrics.json + output/triad_runs/*/metrics.json",
                message=message,
            ),
            ParallelSourceStatus(
                name="MonteCarlo",
                ok=False,
                source="VM automation/results/*/metrics.json + output/triad_runs/*/metrics.json",
                message=message,
            ),
        ]
        return [], status

    rows = _parse_vm_rows(result.stdout)
    counts = {"Approach1": 0, "Approach2": 0, "MonteCarlo": 0}
    for row in rows:
        counts[_classify_vm_record(row)] += 1

    return rows, [
        ParallelSourceStatus(
            name="Approach1",
            ok=True,
            source="VM automation/results/*/metrics.json + output/triad_runs/*/metrics.json",
            records_found=counts["Approach1"],
        ),
        ParallelSourceStatus(
            name="Approach2",
            ok=True,
            source="VM automation/results/*/metrics.json + output/triad_runs/*/metrics.json",
            records_found=counts["Approach2"],
        ),
        ParallelSourceStatus(
            name="MonteCarlo",
            ok=True,
            source="VM automation/results/*/metrics.json + output/triad_runs/*/metrics.json",
            records_found=counts["MonteCarlo"],
        ),
    ]


def _collect_sql_metric_rows() -> tuple[list[dict[str, Any]], dict[str, int]]:
    session = SessionLocal()
    try:
        experiments = (
            session.query(models.Experiment)
            .filter(models.Experiment.status == "completed")
            .all()
        )
        rows = []
        counts = {"Approach1": 0, "Approach2": 0, "MonteCarlo": 0}
        for experiment in experiments:
            if not isinstance(experiment.metrics, dict) or not experiment.metrics:
                continue
            label = classify_experiment(
                name=experiment.name,
                model_type=experiment.model_type,
                parameters=experiment.parameters if isinstance(experiment.parameters, dict) else None,
                metrics=experiment.metrics,
            )
            rows.append(
                {
                    "trial_id": experiment.experiment_id,
                    "path": "approach_2.experiments.metrics",
                    "metrics": experiment.metrics,
                    "approach_label": label,
                    "created_at": experiment.created_at.isoformat() if experiment.created_at else "",
                }
            )
            counts[label] += 1
    finally:
        session.close()

    return rows, counts


def _parse_vm_rows(stdout: str) -> list[dict[str, Any]]:
    if not stdout.strip():
        return []
    payload_line = stdout.strip().splitlines()[-1]
    try:
        payload = json.loads(payload_line)
    except json.JSONDecodeError:
        return []
    rows = payload.get("rows", [])
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _classify_vm_record(row: dict[str, Any]) -> str:
    metrics = _record_metrics(row)
    trial_id = str(row.get("trial_id", "")).lower()
    path = str(row.get("path", "")).lower()
    approach_label = str(metrics.get("approach_label", "")).lower()

    if (
        trial_id.startswith("mc_")
        or "mc_" in trial_id
        or "mc_" in path
        or "monte" in trial_id
        or "monte" in path
        or "monte" in approach_label
        or _metric_value(metrics, ("stability_score", "stable_score")) is not None
    ):
        return "MonteCarlo"

    if (
        trial_id.startswith("a2_")
        or "/a2_" in path
        or "\\a2_" in path
        or "approach2" in approach_label
        or "approach_2" in approach_label
        or str(row.get("approach_label", "")) == "Approach2"
    ):
        return "Approach2"

    return "Approach1"


def _select_best_record(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None

    scored: list[tuple[float, dict[str, Any]]] = []
    for row in rows:
        score = _score_record(row)
        if score is not None:
            scored.append((score, row))

    if scored:
        return max(scored, key=lambda item: item[0])[1]
    return rows[0]


def _select_record_for_label(label: str, rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if label != "MonteCarlo":
        return _select_latest_record(rows) or _select_best_record(rows)
    if not rows:
        return None

    existing = [row for row in rows if _metric_value(_record_metrics(row), ("stability_score", "stable_score")) is not None]
    if existing:
        return _select_latest_record(existing) or _select_best_record(existing)

    accuracies = _collect_numbers(rows, ("best_val_accuracy", "val_accuracy", "accuracy"))
    aurocs = _collect_numbers(rows, ("val_auroc_ovr_macro", "mean_auroc", "auroc", "auc", "roc_auc", "val_auroc"))
    f1_scores = _collect_numbers(rows, ("final_val_f1_macro", "f1", "f1_score", "mean_f1", "val_f1", "val_f1_macro"))

    metrics: dict[str, Any] = {
        "approach_label": "MonteCarlo",
        "completed_trials": len(rows),
    }
    if accuracies:
        metrics["best_val_accuracy"] = max(accuracies)
        metrics["mean_accuracy"] = statistics.fmean(accuracies)
        metrics["stability_score"] = statistics.fmean(accuracies) - 0.5 * _safe_std(accuracies)
    if aurocs:
        metrics["val_auroc_ovr_macro"] = max(aurocs)
        metrics["mean_auroc"] = statistics.fmean(aurocs)
        metrics["sd_auroc"] = _safe_std(aurocs)
    if f1_scores:
        metrics["final_val_f1_macro"] = max(f1_scores)
        metrics["mean_f1"] = statistics.fmean(f1_scores)

    return {
        "trial_id": "monte_carlo_suite",
        "path": "approach_2.experiments.metrics",
        "metrics": metrics,
        "approach_label": "MonteCarlo",
    }


def _select_latest_record(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None
    return max(rows, key=lambda row: str(row.get("created_at", "")))


def _score_record(row: dict[str, Any]) -> float | None:
    metrics = _record_metrics(row)
    for aliases in SCORE_ALIASES:
        value = _metric_value(metrics, aliases)
        if value is not None:
            return value
    return None


def _record_metrics(row: dict[str, Any] | None) -> dict[str, Any]:
    if not row:
        return {}
    metrics = row.get("metrics", row)
    return metrics if isinstance(metrics, dict) else {}


def _metric_value(metrics: dict[str, Any], aliases: tuple[str, ...]) -> float | None:
    for alias in aliases:
        if alias in metrics:
            value = _as_number(metrics[alias])
            if value is not None:
                return value
    return None


def _collect_numbers(rows: list[dict[str, Any]], aliases: tuple[str, ...]) -> list[float]:
    values: list[float] = []
    for row in rows:
        value = _metric_value(_record_metrics(row), aliases)
        if value is not None:
            values.append(value)
    return values


def _safe_std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    return statistics.stdev(values)


def _as_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str):
        try:
            number = float(value)
        except ValueError:
            return None
    else:
        return None

    return number if math.isfinite(number) else None
