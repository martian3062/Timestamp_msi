from __future__ import annotations

import json
import uuid
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
)

TCGA_SLIDE_TRIAD_PRESETS: tuple[dict[str, Any], ...] = (
    {
        "name_suffix": "approach1-transmil-seed310",
        "approach_label": "Approach1",
        "mil_model": "transmil",
        "epochs": 8,
        "seed": 310,
    },
    {
        "name_suffix": "approach2-attention-seed310",
        "approach_label": "Approach2",
        "mil_model": "attention_mil",
        "epochs": 12,
        "seed": 310,
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


def build_tcga_slide_triad_specs(request: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    bundle_id = str(uuid.uuid4())[:8]
    specs: list[dict[str, Any]] = []
    for preset in TCGA_SLIDE_TRIAD_PRESETS:
        spec = dict(request)
        spec.update(
            {
                "bundle_id": bundle_id,
                "experiment_id": str(uuid.uuid4())[:8],
                "experiment_name": f"{request.get('experiment_name', 'tcga-coad-20-slide-triad')}-{preset['name_suffix']}",
                "training_mode": "mil",
                "approach_label": preset["approach_label"],
                "mil_model": preset["mil_model"],
                "epochs": preset["epochs"],
                "seed": preset["seed"],
            }
        )
        specs.append(spec)
    return bundle_id, specs


def tcga_slide_triad_root(bundle_id: str, vm: VmService | None = None) -> str:
    service = vm or VmService()
    return f"{service.settings.vm_project_root}/automation/tcga_slide_triads/{bundle_id}"


def tcga_slide_triad_status_path(bundle_id: str, vm: VmService | None = None) -> str:
    return f"{tcga_slide_triad_root(bundle_id, vm)}/status.json"


def enqueue_triad_experiments(specs: list[dict[str, Any]]) -> list[models.Experiment]:
    session = SessionLocal()
    try:
        created: list[models.Experiment] = []
        for spec in specs:
            experiment = models.Experiment(
                experiment_id=spec["experiment_id"],
                name=spec["experiment_name"],
                model_type=str(spec.get("training_mode") if spec.get("training_mode") != "mil" else spec.get("mil_model") or spec.get("model_type") or "patch_classification"),
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


def run_tcga_slide_triad_bundle(bundle_id: str, request: dict[str, Any], specs: list[dict[str, Any]]) -> None:
    vm = VmService()
    _ensure_remote_scripts(vm)
    bundle_root = tcga_slide_triad_root(bundle_id, vm)
    status_path = tcga_slide_triad_status_path(bundle_id, vm)

    for spec in specs:
        _update_experiment(
            str(spec["experiment_id"]),
            status="running",
            metrics={
                "stage": "queued_remote_tcga_slide_triad",
                "bundle_id": bundle_id,
                "approach_label": spec["approach_label"],
                "bucket_uri": request.get("bucket_uri"),
                "remote_status_path": status_path,
            },
        )

    bundle_payload = {
        "bundle_id": bundle_id,
        "request": request,
        "specs": specs,
        "bundle_root": bundle_root,
        "status_path": status_path,
    }
    vm.write_project_file(
        f"automation/tcga_slide_triads/{bundle_id}/bundle_config.json",
        json.dumps(bundle_payload, indent=2),
        action="syncTcgaSlideTriadBundleConfig",
        timeout=120,
    )

    command = (
        "source /opt/miniforge3/etc/profile.d/conda.sh && "
        "conda activate pathology310 && "
        "RUNNER_PYTHON=/home/pardeep/.venvs/pathology310-fastai/bin/python; "
        "if [ ! -x \"$RUNNER_PYTHON\" ]; then RUNNER_PYTHON=$(command -v python); fi; "
        "\"$RUNNER_PYTHON\" scripts/run_tcga_coad_automated_triad.py "
        f"--bundle-config '{bundle_root}/bundle_config.json'"
    )
    result = vm.run_project_command(
        "runTcgaSlideTriadBundle",
        command,
        timeout=43200,
    )
    if not result.ok:
        for spec in specs:
            _update_experiment(
                str(spec["experiment_id"]),
                status="failed",
                metrics={
                    "bundle_id": bundle_id,
                    "approach_label": spec["approach_label"],
                    "error": result.stderr or result.stdout or "Remote TCGA slide triad runner failed.",
                    "remote_status_path": status_path,
                },
            )
        return

    summary_result = vm.run_project_command(
        "readTcgaSlideTriadSummary",
        f"cat '{bundle_root}/final_summary.json'",
        timeout=120,
    )
    summary = json.loads(summary_result.stdout) if summary_result.ok and summary_result.stdout else {}
    approaches = summary.get("approaches", {}) if isinstance(summary, dict) else {}

    for spec in specs:
        approach_label = str(spec["approach_label"])
        approach_summary = approaches.get(approach_label, {})
        experiment_metrics = {
            "bundle_id": bundle_id,
            "approach_label": approach_label,
            "remote_status_path": status_path,
            **(approach_summary if isinstance(approach_summary, dict) else {}),
        }
        experiment_status = "completed" if approach_summary else "failed"
        _update_experiment(str(spec["experiment_id"]), status=experiment_status, metrics=experiment_metrics)


def read_tcga_slide_triad_status(bundle_id: str) -> dict[str, Any]:
    vm = VmService()
    status_path = tcga_slide_triad_status_path(bundle_id, vm)
    result = vm.run_project_command(
        "readTcgaSlideTriadStatus",
        f"cat '{status_path}'",
        timeout=120,
    )
    if not result.ok:
        return {
            "bundle_id": bundle_id,
            "state": "missing",
            "error": result.stderr or result.stdout or "Unable to read remote status.",
        }
    try:
        payload = json.loads(result.stdout)
        if isinstance(payload, dict):
            payload = _augment_tcga_slide_triad_status(vm, bundle_id, payload)
        return payload
    except json.JSONDecodeError:
        return {
            "bundle_id": bundle_id,
            "state": "invalid",
            "raw": result.stdout,
        }


def read_latest_tcga_slide_triad_status() -> dict[str, Any]:
    vm = VmService()
    root = f"{vm.settings.vm_project_root}/automation/tcga_slide_triads"
    command = f"""python3 - <<'PY'
import json
from pathlib import Path

root = Path({root!r})
candidates = []

if root.exists():
    for child in root.iterdir():
        if not child.is_dir():
            continue
        status_path = child / "status.json"
        if not status_path.exists():
            continue
        try:
            payload = json.loads(status_path.read_text())
        except Exception:
            continue
        updated = payload.get("updated_at_epoch")
        if not isinstance(updated, (int, float)):
            updated = status_path.stat().st_mtime
        candidates.append((-float(updated), child.name))

if not candidates:
    print(json.dumps({{}}))
else:
    candidates.sort()
    print(json.dumps({{"bundle_id": candidates[0][1]}}))
PY"""
    result = vm.run_project_command("readLatestTcgaSlideTriadStatus", command, timeout=120)
    if not result.ok or not result.stdout:
        return {
            "bundle_id": "",
            "remote_status_path": "",
            "status": {"state": "missing", "error": result.stderr or result.stdout or "Unable to inspect remote triad bundles."},
        }
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {
            "bundle_id": "",
            "remote_status_path": "",
            "status": {"state": "invalid", "raw": result.stdout},
        }
    bundle_id = str(payload.get("bundle_id") or "")
    if not bundle_id:
        return {
            "bundle_id": "",
            "remote_status_path": "",
            "status": {"state": "missing", "error": "No TCGA triad bundle was found on the VM."},
        }
    return {
        "bundle_id": bundle_id,
        "remote_status_path": tcga_slide_triad_status_path(bundle_id, vm),
        "status": read_tcga_slide_triad_status(bundle_id),
    }


def _augment_tcga_slide_triad_status(
    vm: VmService,
    bundle_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    state = str(payload.get("state") or "")
    if state not in {"extracting_tiles", "retrying_tiles", "generating_features", "prepared", "training_parallel"}:
        return payload

    bundle_root = tcga_slide_triad_root(bundle_id, vm)
    progress_command = (
        "python3 -c \""
        "import json; "
        "from pathlib import Path; "
        f"tfrecords = Path('{bundle_root}/slideflow_project/tfrecords'); "
        f"bags = Path('{bundle_root}/slideflow_project/bags'); "
        "tf_files = [p for p in tfrecords.rglob('*') if p.is_file()] if tfrecords.exists() else []; "
        "bag_files = [p for p in bags.rglob('*') if p.is_file()] if bags.exists() else []; "
        "payload = {"
        "'tfrecord_files': len(tf_files), "
        "'tfrecord_bytes': sum(p.stat().st_size for p in tf_files), "
        "'bag_files': len(bag_files), "
        "'bag_bytes': sum(p.stat().st_size for p in bag_files)"
        "}; "
        "print(json.dumps(payload))\""
    )
    progress_result = vm.run_project_command(
        "readTcgaSlideTriadProgress",
        progress_command,
        timeout=120,
    )
    if not progress_result.ok or not progress_result.stdout:
        return payload
    try:
        progress_payload = json.loads(progress_result.stdout)
    except json.JSONDecodeError:
        return payload
    if isinstance(progress_payload, dict):
        payload.update(progress_payload)
    return payload


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
    tcga_slide_triad_script = (repo_root / "scripts" / "run_tcga_coad_automated_triad.py").read_text(encoding="utf-8")
    vm.write_project_file("scripts/train_crc_patch_training.py", train_script, action="syncTrainPatchScript", mode="755", timeout=120)
    vm.write_project_file("scripts/predict_crc_patch_image.py", predict_script, action="syncPredictPatchScript", mode="755", timeout=120)
    vm.write_project_file("scripts/run_tcga_coad_automated_triad.py", tcga_slide_triad_script, action="syncTcgaSlideTriadScript", mode="755", timeout=120)


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
