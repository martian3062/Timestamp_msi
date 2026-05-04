#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from random import Random
from typing import Any


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def distribute(total: int, n_parts: int) -> list[int]:
    base = total // n_parts
    extra = total % n_parts
    return [base + (1 if idx < extra else 0) for idx in range(n_parts)]


def make_batches(
    rows: list[dict[str, str]],
    *,
    batch_count: int,
    batch_size: int,
    seed: int,
) -> list[list[dict[str, str]]]:
    pos = [row for row in rows if row["msi_status"] == "MSI-H"]
    neg = [row for row in rows if row["msi_status"] == "MSS"]
    rng = Random(seed)
    rng.shuffle(pos)
    rng.shuffle(neg)

    target_total = min(len(rows), batch_count * batch_size)
    pos_to_use = min(len(pos), target_total)
    neg_to_use = min(len(neg), target_total - pos_to_use)
    pos = pos[:pos_to_use]
    neg = neg[:neg_to_use]

    pos_counts = distribute(len(pos), batch_count)
    neg_counts = [batch_size - count for count in pos_counts]

    batches: list[list[dict[str, str]]] = []
    pos_index = 0
    neg_index = 0
    for idx in range(batch_count):
        batch = pos[pos_index : pos_index + pos_counts[idx]] + neg[neg_index : neg_index + neg_counts[idx]]
        pos_index += pos_counts[idx]
        neg_index += neg_counts[idx]
        batch.sort(key=lambda row: (row["sample_id"], row["slide"]))
        batches.append(batch)
    return batches


def build_bundle_config(
    *,
    project_root: Path,
    bundle_id: str,
    experiment_name: str,
    annotations_relpath: str,
    bucket_uri: str,
    slide_limit: int,
    n_folds: int,
    feature_extractor: str,
    max_tiles_per_slide: int,
    mpp_override: float,
    qc_method: str,
) -> dict[str, Any]:
    bundle_root = project_root / "automation" / "tcga_slide_triads" / bundle_id
    status_path = bundle_root / "status.json"
    shared = {
        "bucket_uri": bucket_uri,
        "slide_limit": slide_limit,
        "n_folds": n_folds,
        "preferred_slide_pattern": "DX",
        "preferred_exact_suffix": "DX1",
        "annotations_csv": annotations_relpath,
        "feature_extractor": feature_extractor,
        "tile_px": 256,
        "tile_um": 128,
        "max_parallel_approaches": 2,
        "max_tiles_per_slide": max_tiles_per_slide,
        "mpp_override": mpp_override,
        "qc_method": qc_method,
    }
    return {
        "bundle_id": bundle_id,
        "bundle_root": str(bundle_root),
        "status_path": str(status_path),
        "request": {"experiment_name": experiment_name, **shared},
        "specs": [
            {
                "experiment_name": f"{experiment_name}-approach1-transmil-seed310",
                **shared,
                "bundle_id": bundle_id,
                "experiment_id": f"{bundle_id}_a1",
                "training_mode": "mil",
                "approach_label": "Approach1",
                "mil_model": "transmil",
                "epochs": 6,
                "seed": 310,
            },
            {
                "experiment_name": f"{experiment_name}-approach2-attention-seed310",
                **shared,
                "bundle_id": bundle_id,
                "experiment_id": f"{bundle_id}_a2",
                "training_mode": "mil",
                "approach_label": "Approach2",
                "mil_model": "attention_mil",
                "epochs": 8,
                "seed": 310,
            },
        ],
    }


def run_bundle(python_bin: str, runner_script: Path, bundle_config_path: Path, bundle_root: Path) -> int:
    bundle_root.mkdir(parents=True, exist_ok=True)
    runner_log = bundle_root / "runner.log"
    env = dict(**os.environ)
    env.setdefault("CONDA_PREFIX", str(Path(python_bin).resolve().parents[1]))
    with runner_log.open("w", encoding="utf-8") as handle:
        proc = subprocess.run(
            [python_bin, str(runner_script), "--bundle-config", str(bundle_config_path)],
            cwd=str(bundle_root),
            env=env,
            stdout=handle,
            stderr=subprocess.STDOUT,
            check=False,
        )
    return int(proc.returncode)


def archive_bundle(bundle_root: Path, archive_dir: Path, batch_rows: list[dict[str, str]]) -> dict[str, Any]:
    archive_dir.mkdir(parents=True, exist_ok=True)
    write_csv_rows(archive_dir / "batch_annotations.csv", batch_rows)

    copied: dict[str, str] = {}
    for rel_path in [
        "status.json",
        "final_summary.json",
        "prepared_bundle.json",
        "runner.log",
        "approaches/Approach1/metrics.json",
        "approaches/Approach2/metrics.json",
        "approaches/Approach1/fold_metrics.csv",
        "approaches/Approach2/fold_metrics.csv",
    ]:
        src = bundle_root / rel_path
        if src.exists():
            dest = archive_dir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            copied[rel_path] = str(dest)

    summary_path = archive_dir / "final_summary.json"
    status_path = archive_dir / "status.json"
    return {
        "archive_dir": str(archive_dir),
        "copied": copied,
        "final_summary_exists": summary_path.exists(),
        "status_exists": status_path.exists(),
    }


def cleanup_bundle(bundle_root: Path) -> None:
    shutil.rmtree(bundle_root, ignore_errors=True)


def extract_batch_result(bundle_id: str, archive_dir: Path, batch_rows: list[dict[str, str]], return_code: int) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "bundle_id": bundle_id,
        "archive_dir": str(archive_dir),
        "return_code": return_code,
        "slide_count": len(batch_rows),
        "label_counts": dict(Counter(row["msi_status"] for row in batch_rows)),
    }
    summary_path = archive_dir / "final_summary.json"
    status_path = archive_dir / "status.json"
    if summary_path.exists():
        payload["final_summary"] = json.loads(summary_path.read_text(encoding="utf-8"))
    if status_path.exists():
        payload["status"] = json.loads(status_path.read_text(encoding="utf-8"))
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Run four sequential TCGA DX1 training batches with cleanup between runs.")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--runner-script", required=True)
    parser.add_argument("--python-bin", required=True)
    parser.add_argument("--source-annotations", required=True)
    parser.add_argument("--bucket-uri", required=True)
    parser.add_argument("--batch-prefix", default="live1360dx1batch")
    parser.add_argument("--archive-root", required=True)
    parser.add_argument("--batch-count", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--seed", type=int, default=310)
    parser.add_argument("--n-folds", type=int, default=2)
    parser.add_argument("--max-tiles-per-slide", type=int, default=48)
    parser.add_argument("--mpp-override", type=float, default=0.25)
    parser.add_argument("--qc-method", default="otsu")
    args = parser.parse_args()

    project_root = Path(args.project_root)
    runner_script = Path(args.runner_script)
    source_annotations = Path(args.source_annotations)
    archive_root = Path(args.archive_root)
    archive_root.mkdir(parents=True, exist_ok=True)

    rows = read_csv_rows(source_annotations)
    batches = make_batches(rows, batch_count=args.batch_count, batch_size=args.batch_size, seed=args.seed)

    orchestration_summary: dict[str, Any] = {
        "started_at_epoch": time.time(),
        "source_annotations": str(source_annotations),
        "bucket_uri": args.bucket_uri,
        "batch_count": args.batch_count,
        "batch_size": args.batch_size,
        "seed": args.seed,
        "results": [],
    }
    write_json(archive_root / "orchestration_status.json", orchestration_summary)

    for idx, batch_rows in enumerate(batches, start=1):
        bundle_id = f"{args.batch_prefix}_{idx:02d}"
        batch_csv_rel = f"automation/batch_inputs/{bundle_id}.csv"
        batch_csv_abs = project_root / batch_csv_rel
        write_csv_rows(batch_csv_abs, batch_rows)

        config = build_bundle_config(
            project_root=project_root,
            bundle_id=bundle_id,
            experiment_name=bundle_id,
            annotations_relpath=batch_csv_rel,
            bucket_uri=args.bucket_uri,
            slide_limit=len(batch_rows),
            n_folds=args.n_folds,
            feature_extractor="ctranspath,resnet50_imagenet",
            max_tiles_per_slide=args.max_tiles_per_slide,
            mpp_override=args.mpp_override,
            qc_method=args.qc_method,
        )

        bundle_root = Path(config["bundle_root"])
        bundle_config_path = bundle_root / "bundle_config.json"
        write_json(bundle_config_path, config)

        return_code = run_bundle(args.python_bin, runner_script, bundle_config_path, bundle_root)
        archive_dir = archive_root / bundle_id
        archive_bundle(bundle_root, archive_dir, batch_rows)
        result = extract_batch_result(bundle_id, archive_dir, batch_rows, return_code)
        orchestration_summary["results"].append(result)
        write_json(archive_root / "orchestration_status.json", orchestration_summary)

        cleanup_bundle(bundle_root)
        if return_code != 0:
            orchestration_summary["failed_bundle_id"] = bundle_id
            orchestration_summary["finished_at_epoch"] = time.time()
            write_json(archive_root / "orchestration_status.json", orchestration_summary)
            raise SystemExit(return_code)

    orchestration_summary["finished_at_epoch"] = time.time()
    write_json(archive_root / "orchestration_status.json", orchestration_summary)


if __name__ == "__main__":
    main()
