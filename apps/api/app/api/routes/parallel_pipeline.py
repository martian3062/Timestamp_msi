from __future__ import annotations

import json
import math
import uuid
from typing import Any, Literal

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app.approach_2.database import models
from app.approach_2.database.setup import SessionLocal
from app.services.vm import VmService

router = APIRouter()


METRIC_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("AUROC", ("mean_auroc", "auroc", "auc", "roc_auc", "val_auroc")),
    ("AUPRC", ("mean_auprc", "auprc", "average_precision", "val_auprc")),
    ("F1 Score", ("f1", "f1_score", "mean_f1", "val_f1")),
    ("Sensitivity", ("msi_h_sensitivity", "sensitivity", "recall", "val_recall")),
    ("Specificity", ("specificity", "val_specificity")),
    ("Balanced Accuracy", ("balanced_accuracy", "balanced_acc", "val_balanced_accuracy")),
    ("Stable Score", ("stability_score", "stable_score")),
)

SCORE_ALIASES: tuple[tuple[str, ...], ...] = (
    ("stability_score", "stable_score"),
    ("mean_auroc", "auroc", "auc", "roc_auc", "val_auroc"),
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

    vm_rows, vm_status = _collect_vm_metric_rows()
    sources.extend(vm_status)
    for row in vm_rows:
        trial_id = str(row.get("trial_id", ""))
        metrics = _record_metrics(row)
        if trial_id.startswith("mc_") or _metric_value(metrics, ("stability_score", "stable_score")) is not None:
            records["MonteCarlo"].append(row)
        else:
            records["Approach1"].append(row)

    approach2_rows, approach2_status = _collect_approach2_metric_rows()
    records["Approach2"].extend(approach2_rows)
    sources.append(approach2_status)

    return records, sources


def build_parallel_metrics(records: dict[str, list[dict[str, Any]]]) -> list[ParallelMetric]:
    selected = {
        name: _select_best_record(rows)
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
for path in sorted(Path("automation/results").glob("*/metrics.json")):
    try:
        data = json.loads(path.read_text())
    except Exception:
        continue
    rows.append({
        "trial_id": data.get("trial_id", path.parent.name),
        "path": str(path),
        "metrics": data,
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
                source="VM automation/results/*/metrics.json",
                message=message,
            ),
            ParallelSourceStatus(
                name="MonteCarlo",
                ok=False,
                source="VM automation/results/*/metrics.json",
                message=message,
            ),
        ]
        return [], status

    rows = _parse_vm_rows(result.stdout)
    approach1_count = 0
    monte_carlo_count = 0
    for row in rows:
        metrics = _record_metrics(row)
        trial_id = str(row.get("trial_id", ""))
        if trial_id.startswith("mc_") or _metric_value(metrics, ("stability_score", "stable_score")) is not None:
            monte_carlo_count += 1
        else:
            approach1_count += 1

    return rows, [
        ParallelSourceStatus(
            name="Approach1",
            ok=True,
            source="VM automation/results/*/metrics.json",
            records_found=approach1_count,
        ),
        ParallelSourceStatus(
            name="MonteCarlo",
            ok=True,
            source="VM automation/results/*/metrics.json",
            records_found=monte_carlo_count,
        ),
    ]


def _collect_approach2_metric_rows() -> tuple[list[dict[str, Any]], ParallelSourceStatus]:
    session = SessionLocal()
    try:
        experiments = (
            session.query(models.Experiment)
            .filter(models.Experiment.status == "completed")
            .all()
        )
        rows = [
            {
                "trial_id": experiment.experiment_id,
                "path": "approach_2.experiments.metrics",
                "metrics": experiment.metrics or {},
            }
            for experiment in experiments
            if isinstance(experiment.metrics, dict) and experiment.metrics
        ]
    finally:
        session.close()

    return rows, ParallelSourceStatus(
        name="Approach2",
        ok=True,
        source="Approach 2 SQLAlchemy experiments.metrics",
        records_found=len(rows),
    )


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
