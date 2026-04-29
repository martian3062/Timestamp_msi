from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..database import models
from ..database.setup import SessionLocal
from .dataset_sources import (
    DEFAULT_LOCAL_DATASET_PATH,
    DEFAULT_WORKSPACE_ROOT,
    resolve_remote_dataset_path,
)
from .experiment_labels import classify_experiment, normalize_approach_label
from app.services.vm import VmService


TRIAD_PRESETS: tuple[dict[str, Any], ...] = (
    {
        "name_suffix": "approach1-resnet34-seed310",
        "approach_label": "Approach1",
        "backbone": "resnet34",
        "epochs": 5,
        "seed": 310,
    },
    {
        "name_suffix": "approach2-resnet18-seed310",
        "approach_label": "Approach2",
        "backbone": "resnet18",
        "epochs": 10,
        "seed": 310,
    },
    {
        "name_suffix": "approach3-resnet18-seed42",
        "approach_label": "MonteCarlo",
        "backbone": "resnet18",
        "epochs": 4,
        "seed": 42,
    },
    {
        "name_suffix": "approach3-resnet18-seed2026",
        "approach_label": "MonteCarlo",
        "backbone": "resnet18",
        "epochs": 4,
        "seed": 2026,
    },
    {
        "name_suffix": "approach3-resnet34-seed777",
        "approach_label": "MonteCarlo",
        "backbone": "resnet34",
        "epochs": 4,
        "seed": 777,
    },
)


def build_triad_specs(request: dict[str, Any]) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for preset in TRIAD_PRESETS:
        spec = dict(request)
        spec.update(
            {
                "training_mode": "patch_classification",
                "experiment_name": f"{request.get('experiment_name', 'crc-triad')}-{preset['name_suffix']}",
                "approach_label": preset["approach_label"],
                "backbone": preset["backbone"],
                "epochs": preset["epochs"],
                "seed": preset["seed"],
                "dataset_path": str(request.get("dataset_path") or DEFAULT_LOCAL_DATASET_PATH),
                "workspace_root": str(request.get("workspace_root") or DEFAULT_WORKSPACE_ROOT),
            }
        )
        specs.append(spec)
    return specs


def build_single_patch_spec(request: dict[str, Any], experiment_id: str) -> dict[str, Any]:
    spec = dict(request)
    spec.update(
        {
            "experiment_id": experiment_id,
            "training_mode": "patch_classification",
            "dataset_path": str(request.get("dataset_path") or DEFAULT_LOCAL_DATASET_PATH),
            "workspace_root": str(request.get("workspace_root") or DEFAULT_WORKSPACE_ROOT),
        }
    )
    return spec


def enqueue_triad_experiments(specs: list[dict[str, Any]]) -> list[models.Experiment]:
    session = SessionLocal()
    try:
        created: list[models.Experiment] = []
        for spec in specs:
            experiment = models.Experiment(
                experiment_id=spec["experiment_id"],
                name=spec["experiment_name"],
                model_type="patch_classification",
                status="running",
                parameters=spec,
            )
            session.add(experiment)
            created.append(experiment)
        session.commit()
        for experiment in created:
            session.refresh(experiment)
        return created
    finally:
        session.close()


def run_crc_triad_bundle(specs: list[dict[str, Any]]) -> None:
    for spec in specs:
        run_vm_patch_experiment(spec)
    _upsert_monte_carlo_summary(specs)


def run_single_vm_patch_experiment(spec: dict[str, Any]) -> None:
    run_vm_patch_experiment(spec)


def run_vm_patch_experiment(spec: dict[str, Any]) -> None:
    vm = VmService()
    experiment_id = str(spec["experiment_id"])
    _ensure_remote_scripts(vm)
    _update_experiment(experiment_id, status="running", metrics={"stage": "remote_training", **spec})

    remote_dataset_path, stage_commands = resolve_remote_dataset_path(spec, experiment_id)
    output_dir = f"{vm.settings.vm_project_root}/output/triad_runs/{experiment_id}"

    command_parts = [
        f"cd '{vm.settings.vm_project_root}'",
        "source /opt/miniforge3/etc/profile.d/conda.sh",
        "conda activate pathology310",
    ]
    command_parts.extend(stage_commands)
    command_parts.append(
        "python scripts/train_crc_patch_training.py "
        f"--dataset-path '{remote_dataset_path}' "
        f"--output-dir '{output_dir}' "
        f"--backbone '{spec['backbone']}' "
        f"--epochs {int(spec['epochs'])} "
        f"--batch-size {int(spec.get('batch_size', 32))} "
        f"--learning-rate {float(spec.get('learning_rate', 1e-4))} "
        f"--image-size {int(spec.get('image_size', 224))} "
        f"--val-split {float(spec.get('val_split', 0.2))} "
        f"--num-workers {int(spec.get('num_workers', 0))} "
        f"--seed {int(spec.get('seed', 310))} "
        "--use-pretrained"
    )
    result = vm.run_project_command(
        "runCrcPatchExperiment",
        " && ".join(command_parts),
        timeout=7200,
    )
    if not result.ok:
        _update_experiment(
            experiment_id,
            status="failed",
            metrics={
                "error": result.stderr or result.stdout or "VM training failed.",
                "approach_label": spec["approach_label"],
                "dataset_path": remote_dataset_path,
            },
        )
        return

    metrics_result = vm.run_project_command(
        "readCrcPatchMetrics",
        f"cat '{output_dir}/metrics.json'",
        timeout=120,
    )
    if not metrics_result.ok:
        _update_experiment(
            experiment_id,
            status="failed",
            metrics={
                "error": metrics_result.stderr or metrics_result.stdout or "Unable to read remote metrics.",
                "approach_label": spec["approach_label"],
            },
        )
        return

    metrics = json.loads(metrics_result.stdout)
    metrics["approach_label"] = spec["approach_label"]
    metrics["dataset_source"] = spec.get("dataset_source", "workspace_root")
    metrics["workspace_root"] = spec.get("workspace_root", str(DEFAULT_WORKSPACE_ROOT))
    _update_experiment(experiment_id, status="completed", metrics=metrics)


def predict_uploaded_patch(
    *,
    file_bytes: bytes,
    filename: str,
    experiment_id: str | None,
    approach_label: str,
) -> dict[str, Any]:
    experiment = _find_experiment(experiment_id=experiment_id, approach_label=approach_label)
    if experiment is None or not isinstance(experiment.metrics, dict):
        raise ValueError("No completed experiment is available for prediction.")

    metrics = experiment.metrics
    artifacts = metrics.get("artifacts", {}) if isinstance(metrics, dict) else {}
    model_path = str(artifacts.get("model_path") or "")
    dataset_path = str(metrics.get("dataset_path") or "")
    backbone = str(metrics.get("backbone") or "resnet18")
    image_size = int(metrics.get("image_size") or 224)

    if not model_path.startswith("/home/"):
        raise ValueError("Prediction upload currently supports VM-backed triad models only.")

    vm = VmService()
    _ensure_remote_scripts(vm)
    safe_name = filename.replace(" ", "_")
    remote_path = f"temp_uploads/{experiment.experiment_id}_{safe_name}"
    vm.write_project_binary_file(remote_path, file_bytes, action="uploadPredictionPatch", timeout=90)
    result = vm.run_project_command(
        "predictUploadedPatch",
        (
            "source /opt/miniforge3/etc/profile.d/conda.sh && "
            "conda activate pathology310 && "
            "python scripts/predict_crc_patch_image.py "
            f"--image-path '{vm.project_path(remote_path)}' "
            f"--model-path '{model_path}' "
            f"--dataset-path '{dataset_path}' "
            f"--backbone '{backbone}' "
            f"--image-size {image_size}"
        ),
        timeout=300,
    )
    if not result.ok:
        raise ValueError(result.stderr or result.stdout or "Prediction failed on the VM.")
    payload = json.loads(result.stdout.splitlines()[-1])
    payload["experiment_id"] = experiment.experiment_id
    payload["approach_label"] = normalize_approach_label(approach_label or classify_experiment(
        name=experiment.name,
        model_type=experiment.model_type,
        parameters=experiment.parameters if isinstance(experiment.parameters, dict) else None,
        metrics=experiment.metrics if isinstance(experiment.metrics, dict) else None,
    ))
    return payload


def _ensure_remote_scripts(vm: VmService) -> None:
    repo_root = Path(__file__).resolve().parents[5]
    train_script = (repo_root / "scripts" / "run_crc_patch_training.py").read_text(encoding="utf-8")
    predict_script = (repo_root / "scripts" / "predict_crc_patch_image.py").read_text(encoding="utf-8")
    vm.write_project_file("scripts/train_crc_patch_training.py", train_script, action="syncTrainPatchScript", mode="755", timeout=120)
    vm.write_project_file("scripts/predict_crc_patch_image.py", predict_script, action="syncPredictPatchScript", mode="755", timeout=120)


def _update_experiment(experiment_id: str, *, status: str, metrics: dict[str, Any] | None = None) -> None:
    session = SessionLocal()
    try:
        experiment = session.query(models.Experiment).filter(models.Experiment.experiment_id == experiment_id).first()
        if experiment is not None:
            experiment.status = status
            if metrics is not None:
                experiment.metrics = metrics
            session.commit()
    finally:
        session.close()


def _find_experiment(*, experiment_id: str | None, approach_label: str) -> models.Experiment | None:
    session = SessionLocal()
    try:
        if experiment_id:
            return session.query(models.Experiment).filter(models.Experiment.experiment_id == experiment_id).first()
        experiments = (
            session.query(models.Experiment)
            .filter(models.Experiment.status == "completed")
            .order_by(models.Experiment.created_at.desc())
            .all()
        )
        target = normalize_approach_label(approach_label)
        for experiment in experiments:
            label = classify_experiment(
                name=experiment.name,
                model_type=experiment.model_type,
                parameters=experiment.parameters if isinstance(experiment.parameters, dict) else None,
                metrics=experiment.metrics if isinstance(experiment.metrics, dict) else None,
            )
            if label == target:
                return experiment
        return None
    finally:
        session.close()


def _upsert_monte_carlo_summary(specs: list[dict[str, Any]]) -> None:
    mc_specs = [spec for spec in specs if spec.get("approach_label") == "MonteCarlo"]
    if not mc_specs:
        return

    session = SessionLocal()
    try:
        experiments = [
            session.query(models.Experiment)
            .filter(models.Experiment.experiment_id == spec["experiment_id"])
            .first()
            for spec in mc_specs
        ]
        metrics_rows = [
            experiment.metrics
            for experiment in experiments
            if experiment is not None and isinstance(experiment.metrics, dict)
        ]
        if not metrics_rows:
            return

        accuracies = [float(row["best_val_accuracy"]) for row in metrics_rows if row.get("best_val_accuracy") is not None]
        aurocs = [float(row["val_auroc_ovr_macro"]) for row in metrics_rows if row.get("val_auroc_ovr_macro") is not None]
        f1_scores = [float(row["final_val_f1_macro"]) for row in metrics_rows if row.get("final_val_f1_macro") is not None]
        if not accuracies or not aurocs or not f1_scores:
            return

        mean_auroc = sum(aurocs) / len(aurocs)
        if len(aurocs) > 1:
            variance = sum((value - mean_auroc) ** 2 for value in aurocs) / (len(aurocs) - 1)
            sd_auroc = variance ** 0.5
        else:
            sd_auroc = 0.0

        summary_metrics = {
            "approach_label": "MonteCarlo",
            "completed_trials": len(metrics_rows),
            "best_val_accuracy": max(accuracies),
            "mean_accuracy": sum(accuracies) / len(accuracies),
            "val_auroc_ovr_macro": max(aurocs),
            "mean_auroc": mean_auroc,
            "sd_auroc": sd_auroc,
            "final_val_f1_macro": max(f1_scores),
            "mean_f1": sum(f1_scores) / len(f1_scores),
            "stability_score": mean_auroc - 0.5 * sd_auroc,
            "members": [str(spec["experiment_id"]) for spec in mc_specs],
            "dataset_source": mc_specs[0].get("dataset_source", "workspace_root"),
            "workspace_root": mc_specs[0].get("workspace_root", str(DEFAULT_WORKSPACE_ROOT)),
        }

        summary_id = f"{mc_specs[0]['experiment_id'][:4]}-mc-suite"
        summary_name = f"{mc_specs[0]['experiment_name']}-suite-summary"
        existing = session.query(models.Experiment).filter(models.Experiment.experiment_id == summary_id).first()
        if existing is None:
            existing = models.Experiment(
                experiment_id=summary_id,
                name=summary_name,
                model_type="monte_carlo_patch_suite",
                status="completed",
                parameters={"approach_label": "MonteCarlo", "members": summary_metrics["members"]},
                metrics=summary_metrics,
            )
            session.add(existing)
        else:
            existing.name = summary_name
            existing.status = "completed"
            existing.model_type = "monte_carlo_patch_suite"
            existing.parameters = {"approach_label": "MonteCarlo", "members": summary_metrics["members"]}
            existing.metrics = summary_metrics
        session.commit()
    finally:
        session.close()
