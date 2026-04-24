from __future__ import annotations

from app.models.data_batches import DataBatchActionResponse, GdcBatchStartRequest
from app.services.vm import VmService


GDC_BATCH_SCRIPT = r'''"""Download small GDC TCGA-CRC SVS batches and track progress.

The script keeps permanent batch metadata under automation/gdc_batches and
downloads temporary SVS files into slideflow_project/data/slides.
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PROJECT_DIR = Path(__file__).resolve().parents[1]
ANNOTATIONS = PROJECT_DIR / "annotations" / "tcga_crc_msi_annotations.csv"
SLIDES_DIR = PROJECT_DIR / "slideflow_project" / "data" / "slides"
BATCH_ROOT = PROJECT_DIR / "automation" / "gdc_batches"
LEDGER = BATCH_ROOT / "processed_file_ids.json"
GDC_FILES = "https://api.gdc.cancer.gov/files"
GDC_DATA = "https://api.gdc.cancer.gov/data/{file_id}"


def read_json(path: Path, fallback):
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def annotation_patients() -> set[str]:
    if not ANNOTATIONS.exists():
        return set()
    with ANNOTATIONS.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames or []
        patient_col = next(
            (column for column in columns if column.lower() in {"patient", "patient_id", "case", "case_id"}),
            None,
        )
        if not patient_col:
            return set()
        return {row.get(patient_col, "").strip() for row in reader if row.get(patient_col, "").strip()}


def query_gdc(size: int = 2000) -> list[dict]:
    payload = {
        "filters": {
            "op": "and",
            "content": [
                {
                    "op": "in",
                    "content": {
                        "field": "cases.project.project_id",
                        "value": ["TCGA-COAD", "TCGA-READ"],
                    },
                },
                {"op": "=", "content": {"field": "files.data_format", "value": "SVS"}},
                {"op": "=", "content": {"field": "files.access", "value": "open"}},
                {"op": "=", "content": {"field": "files.data_type", "value": "Slide Image"}},
            ],
        },
        "fields": "file_id,file_name,file_size,cases.submitter_id,cases.project.project_id",
        "format": "JSON",
        "size": size,
    }
    request = Request(
        GDC_FILES,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "timestamp-msi-batcher"},
        method="POST",
    )
    with urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))["data"]["hits"]


def case_id(hit: dict) -> str:
    cases = hit.get("cases") or []
    if not cases:
        return ""
    return cases[0].get("submitter_id", "")


def select_batch(limit: int, prefer_dx: bool) -> list[dict]:
    processed = set(read_json(LEDGER, []))
    patients = annotation_patients()
    hits = query_gdc()
    if patients:
        hits = [hit for hit in hits if case_id(hit) in patients]
    if prefer_dx:
        dx_hits = [hit for hit in hits if "-DX" in hit.get("file_name", "")]
        hits = dx_hits or hits
    hits = sorted(hits, key=lambda item: (case_id(item), item.get("file_name", "")))
    return [hit for hit in hits if hit["file_id"] not in processed][:limit]


def download_file(hit: dict, out_dir: Path, retries: int = 4) -> bool:
    out_dir.mkdir(parents=True, exist_ok=True)
    file_id = hit["file_id"]
    file_name = hit["file_name"]
    expected_size = int(hit.get("file_size") or 0)
    destination = out_dir / file_name
    partial = destination.with_suffix(destination.suffix + ".part")
    if destination.exists() and expected_size and destination.stat().st_size == expected_size:
        return True
    if partial.exists():
        partial.unlink()
    for attempt in range(1, retries + 1):
        try:
            request = Request(
                GDC_DATA.format(file_id=file_id),
                headers={"User-Agent": "timestamp-msi-batcher"},
            )
            with urlopen(request, timeout=300) as response, partial.open("wb") as handle:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
            if expected_size and partial.stat().st_size != expected_size:
                raise IOError(f"Size mismatch for {file_name}")
            partial.replace(destination)
            return True
        except (HTTPError, URLError, TimeoutError, IOError) as exc:
            print(f"download_error file={file_name} attempt={attempt} error={exc}", flush=True)
            if partial.exists():
                partial.unlink()
            if attempt == retries:
                return False
            time.sleep(10 * attempt)
    return False


def write_manifest(batch_id: str, rows: list[dict]) -> None:
    manifest = BATCH_ROOT / batch_id / "gdc_manifest_10.tsv"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    with manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "filename", "size", "case_id", "project_id"], delimiter="\t")
        writer.writeheader()
        for hit in rows:
            project_id = ((hit.get("cases") or [{}])[0].get("project") or {}).get("project_id", "")
            writer.writerow(
                {
                    "id": hit["file_id"],
                    "filename": hit["file_name"],
                    "size": hit.get("file_size") or "",
                    "case_id": case_id(hit),
                    "project_id": project_id,
                }
            )


def start(limit: int, prefer_dx: bool) -> None:
    BATCH_ROOT.mkdir(parents=True, exist_ok=True)
    SLIDES_DIR.mkdir(parents=True, exist_ok=True)
    batch = select_batch(limit, prefer_dx)
    batch_id = time.strftime("batch_%Y%m%d_%H%M%S")
    write_manifest(batch_id, batch)
    completed = []
    failed = []
    for hit in batch:
        ok = download_file(hit, SLIDES_DIR)
        (completed if ok else failed).append(hit["file_id"])
    processed = set(read_json(LEDGER, []))
    processed.update(completed)
    write_json(LEDGER, sorted(processed))
    summary = {
        "batch_id": batch_id,
        "requested": limit,
        "selected": len(batch),
        "downloaded": len(completed),
        "failed": len(failed),
        "slide_dir": str(SLIDES_DIR),
        "manifest": str(BATCH_ROOT / batch_id / "gdc_manifest_10.tsv"),
        "completed_file_ids": completed,
        "failed_file_ids": failed,
    }
    write_json(BATCH_ROOT / batch_id / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


def status() -> None:
    summaries = sorted(BATCH_ROOT.glob("batch_*/summary.json"))
    latest = json.loads(summaries[-1].read_text(encoding="utf-8")) if summaries else None
    payload = {
        "svs": len(list(SLIDES_DIR.glob("*.svs"))) if SLIDES_DIR.exists() else 0,
        "partial": len(list(SLIDES_DIR.glob("*.part"))) if SLIDES_DIR.exists() else 0,
        "processed_file_ids": len(read_json(LEDGER, [])),
        "latest_batch": latest,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


def cleanup() -> None:
    deleted = 0
    for pattern in ("*.svs", "*.part"):
        for path in SLIDES_DIR.glob(pattern):
            path.unlink()
            deleted += 1
    print(json.dumps({"deleted": deleted, "slide_dir": str(SLIDES_DIR)}))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["start", "status", "cleanup"])
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--prefer-dx", action="store_true")
    args = parser.parse_args()
    if args.action == "start":
        start(args.limit, args.prefer_dx)
    elif args.action == "cleanup":
        cleanup()
    else:
        status()


if __name__ == "__main__":
    main()
'''


class DataBatchService:
    def __init__(self, vm: VmService | None = None) -> None:
        self.vm = vm or VmService()

    def bootstrap(self) -> DataBatchActionResponse:
        result = self.vm.write_project_file(
            "scripts/run_gdc_svs_batch.py",
            GDC_BATCH_SCRIPT,
            action="bootstrapGdcBatchRunner",
            mode="755",
        )
        return DataBatchActionResponse(
            ok=result.ok,
            action=result.action,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    def start(self, request: GdcBatchStartRequest) -> DataBatchActionResponse:
        prefer = "--prefer-dx" if request.prefer_dx else ""
        command = (
            "mkdir -p automation/logs automation/gdc_batches "
            f"&& nohup pathology310-run python scripts/run_gdc_svs_batch.py start "
            f"--limit {request.limit} {prefer} "
            "> automation/logs/gdc_svs_batch.log 2>&1 & "
            "echo started_gdc_svs_batch"
        )
        result = self.vm.run_project_command("startGdcBatch", command)
        return DataBatchActionResponse(
            ok=result.ok,
            action=result.action,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    def status(self) -> DataBatchActionResponse:
        result = self.vm.run_project_command(
            "gdcBatchStatus",
            (
                "pathology310-run python scripts/run_gdc_svs_batch.py status "
                "&& echo '__LOG__' "
                "&& tail -n 80 automation/logs/gdc_svs_batch.log 2>/dev/null || true"
            ),
            timeout=45,
        )
        return DataBatchActionResponse(
            ok=result.ok,
            action=result.action,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    def cleanup(self) -> DataBatchActionResponse:
        result = self.vm.run_project_command(
            "cleanupGdcBatchSlides",
            "pathology310-run python scripts/run_gdc_svs_batch.py cleanup",
            timeout=45,
        )
        return DataBatchActionResponse(
            ok=result.ok,
            action=result.action,
            stdout=result.stdout,
            stderr=result.stderr,
        )
