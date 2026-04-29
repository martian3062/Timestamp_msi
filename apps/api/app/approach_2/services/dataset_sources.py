from __future__ import annotations

from pathlib import Path
from typing import Any


DEFAULT_WORKSPACE_ROOT = Path(r"E:\4basecare-MSI")
DEFAULT_DATASET_DIRNAME = "CRC-VAL-HE-7K"
DEFAULT_LOCAL_DATASET_PATH = DEFAULT_WORKSPACE_ROOT / DEFAULT_DATASET_DIRNAME
DEFAULT_REMOTE_DATASET_PATH = (
    "/home/pardeep/pathology310_projects/single_slide_morphology/"
    "project_1_slideflow_msi_tcga_crc/datasets/CRC-VAL-HE-7K"
)


def resolve_local_dataset_path(config: dict[str, Any]) -> str:
    source = str(config.get("dataset_source") or "workspace_root")
    if source == "google_bucket":
        bucket_uri = str(config.get("google_bucket_uri") or "").strip()
        if not bucket_uri:
            raise ValueError("A Google bucket URI is required when dataset_source is google_bucket.")
        return bucket_uri

    if source == "workspace_root":
        workspace_root = Path(str(config.get("workspace_root") or DEFAULT_WORKSPACE_ROOT))
        candidate = Path(str(config.get("dataset_path") or "")).expanduser()
        if candidate.is_dir():
            return str(candidate)
        workspace_candidate = workspace_root / DEFAULT_DATASET_DIRNAME
        if workspace_candidate.is_dir():
            return str(workspace_candidate)
        return str(DEFAULT_LOCAL_DATASET_PATH)

    candidate = Path(str(config.get("dataset_path") or DEFAULT_LOCAL_DATASET_PATH)).expanduser()
    return str(candidate)


def resolve_remote_dataset_path(config: dict[str, Any], experiment_id: str) -> tuple[str, list[str]]:
    source = str(config.get("dataset_source") or "workspace_root")
    if source == "google_bucket":
        bucket_uri = str(config.get("google_bucket_uri") or "").strip()
        if not bucket_uri:
            raise ValueError("A Google bucket URI is required when dataset_source is google_bucket.")
        target_dir = (
            "/home/pardeep/pathology310_projects/single_slide_morphology/"
            f"project_1_slideflow_msi_tcga_crc/datasets/staged_{experiment_id}"
        )
        stage_commands = [
            f"rm -rf '{target_dir}'",
            f"mkdir -p '{target_dir}'",
            (
                "if command -v gcloud >/dev/null 2>&1; then "
                f"gcloud storage cp --recursive '{bucket_uri.rstrip('/')}' '{target_dir}'; "
                "elif command -v gsutil >/dev/null 2>&1; then "
                f"gsutil -m cp -r '{bucket_uri.rstrip('/')}'/* '{target_dir}/'; "
                "else echo 'Neither gcloud nor gsutil is installed on the VM.' >&2; exit 1; fi"
            ),
        ]
        return target_dir, stage_commands

    return DEFAULT_REMOTE_DATASET_PATH, []
