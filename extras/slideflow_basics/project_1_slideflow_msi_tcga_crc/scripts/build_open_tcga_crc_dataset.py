"""Build an open TCGA-CRC MSI slide cohort from cBioPortal + GDC.

Outputs:
  annotations/tcga_crc_msi_annotations.csv
  annotations/gdc_manifest_tcga_crc_msi.tsv
  annotations/selected_open_tcga_crc_slides.csv
  annotations/cbioportal_msi_scores.csv

Labels use cBioPortal PanCancer Atlas sample MSI scores:
  MSI-H: MANTIS > 0.6, or MSIsensor > 10 when MANTIS is missing
  MSS:   MANTIS < 0.4, or MSIsensor < 4 when MANTIS is missing
  Indeterminate scores are excluded.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROJECT_DIR = Path(__file__).resolve().parents[1]
ANNOTATIONS_DIR = PROJECT_DIR / "annotations"

CBIO_STUDY_ID = "coadread_tcga_pan_can_atlas_2018"
CBIO_API = "https://www.cbioportal.org/api"
GDC_API = "https://api.gdc.cancer.gov/files"

DEFAULT_MSI_H = 20
DEFAULT_MSS = 40
SEED = 310


def get_json(url: str, params: dict[str, Any] | None = None) -> Any:
    full_url = f"{url}?{urlencode(params, doseq=True)}" if params else url
    req = Request(full_url, headers={"Accept": "application/json"})
    with urlopen(req, timeout=90) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(url: str, payload: dict[str, Any]) -> Any:
    data = json.dumps(payload).encode("utf-8")
    req = Request(
        url,
        data=data,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(req, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_cbioportal_msi_scores() -> list[dict[str, Any]]:
    data = get_json(
        f"{CBIO_API}/studies/{CBIO_STUDY_ID}/clinical-data",
        {
            "clinicalDataType": "SAMPLE",
            "projection": "DETAILED",
            "pageSize": 100000,
        },
    )
    by_sample: dict[str, dict[str, Any]] = defaultdict(dict)
    for row in data:
        attr = row.get("clinicalAttributeId")
        if attr not in {"MSI_SCORE_MANTIS", "MSI_SENSOR_SCORE"}:
            continue
        sample_id = row["sampleId"]
        by_sample[sample_id]["sample_id"] = sample_id
        by_sample[sample_id]["patient"] = row["patientId"]
        by_sample[sample_id][attr] = row.get("value")

    rows = []
    for values in by_sample.values():
        mantis = to_float(values.get("MSI_SCORE_MANTIS"))
        sensor = to_float(values.get("MSI_SENSOR_SCORE"))
        status = classify_msi(mantis, sensor)
        if status is None:
            continue
        rows.append(
            {
                "sample_id": values["sample_id"],
                "patient": values["patient"],
                "msi_score_mantis": mantis,
                "msi_sensor_score": sensor,
                "msi_status": status,
                "label_source": "cBioPortal PanCancer Atlas; MANTIS/MSIsensor thresholds",
            }
        )
    return rows


def to_float(value: Any) -> float | None:
    try:
        if value in {None, "", "NA", "N/A"}:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def classify_msi(mantis: float | None, sensor: float | None) -> str | None:
    if mantis is not None:
        if mantis > 0.6:
            return "MSI-H"
        if mantis < 0.4:
            return "MSS"
        return None
    if sensor is not None:
        if sensor > 10:
            return "MSI-H"
        if sensor < 4:
            return "MSS"
    return None


def fetch_gdc_diagnostic_slides() -> list[dict[str, Any]]:
    fields = [
        "file_id",
        "file_name",
        "md5sum",
        "file_size",
        "state",
        "cases.submitter_id",
        "cases.project.project_id",
        "cases.samples.sample_type",
        "data_type",
        "data_format",
        "experimental_strategy",
    ]
    filters = {
        "op": "and",
        "content": [
            {
                "op": "in",
                "content": {
                    "field": "cases.project.project_id",
                    "value": ["TCGA-COAD", "TCGA-READ"],
                },
            },
            {"op": "in", "content": {"field": "data_type", "value": ["Slide Image"]}},
            {
                "op": "in",
                "content": {
                    "field": "experimental_strategy",
                    "value": ["Diagnostic Slide"],
                },
            },
            {"op": "in", "content": {"field": "data_format", "value": ["SVS"]}},
        ],
    }
    payload = {
        "filters": filters,
        "fields": ",".join(fields),
        "format": "JSON",
        "size": 5000,
    }
    hits = post_json(GDC_API, payload)["data"]["hits"]
    rows = []
    for hit in hits:
        case = hit.get("cases", [{}])[0]
        patient = case.get("submitter_id")
        project = case.get("project", {}).get("project_id", "")
        sample_type = ""
        samples = case.get("samples") or []
        if samples:
            sample_type = samples[0].get("sample_type", "")
        file_name = hit["file_name"]
        slide = file_name[:-4] if file_name.lower().endswith(".svs") else file_name
        rows.append(
            {
                "id": hit.get("file_id") or hit.get("id"),
                "filename": file_name,
                "md5": hit.get("md5sum", ""),
                "size": hit.get("file_size", ""),
                "state": hit.get("state", "released"),
                "slide": slide,
                "patient": patient,
                "project": project,
                "sample_type": sample_type,
                "site": patient.split("-")[1] if patient and "-" in patient else "",
            }
        )
    return rows


def choose_one_slide_per_patient(slides: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in slides:
        if row.get("patient"):
            grouped[row["patient"]].append(row)

    selected = {}
    for patient, patient_slides in grouped.items():
        patient_slides = sorted(
            patient_slides,
            key=lambda r: (
                "DX1" not in r["filename"],
                "Primary Tumor" not in r.get("sample_type", ""),
                r["filename"],
            ),
        )
        selected[patient] = patient_slides[0]
    return selected


def assign_folds(rows: list[dict[str, Any]], n_folds: int = 5) -> None:
    by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_label[row["msi_status"]].append(row)
    for label_rows in by_label.values():
        for idx, row in enumerate(label_rows):
            row["fold"] = (idx % n_folds) + 1


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
    fieldnames: list[str],
    delimiter: str = ",",
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="ignore",
            delimiter=delimiter,
        )
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--msi-h", type=int, default=DEFAULT_MSI_H)
    parser.add_argument("--mss", type=int, default=DEFAULT_MSS)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args(argv)

    random.seed(args.seed)
    ANNOTATIONS_DIR.mkdir(parents=True, exist_ok=True)

    msi_rows = fetch_cbioportal_msi_scores()
    slides = fetch_gdc_diagnostic_slides()
    slide_by_patient = choose_one_slide_per_patient(slides)

    joined = []
    for label in msi_rows:
        slide = slide_by_patient.get(label["patient"])
        if not slide:
            continue
        joined.append({**slide, **label})

    by_status: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in joined:
        by_status[row["msi_status"]].append(row)
    for rows in by_status.values():
        random.shuffle(rows)

    selected = by_status["MSI-H"][: args.msi_h] + by_status["MSS"][: args.mss]
    selected = sorted(selected, key=lambda r: (r["fold"] if "fold" in r else 0, r["msi_status"], r["patient"]))
    random.shuffle(selected)
    assign_folds(selected)
    selected = sorted(selected, key=lambda r: (r["fold"], r["msi_status"], r["patient"]))

    annotations = [
        {
            "slide": row["slide"],
            "patient": row["patient"],
            "msi_status": row["msi_status"],
            "site": row["site"],
            "fold": row["fold"],
            "project": row["project"],
            "gdc_file_id": row["id"],
            "gdc_filename": row["filename"],
            "msi_score_mantis": row["msi_score_mantis"],
            "msi_sensor_score": row["msi_sensor_score"],
            "label_source": row["label_source"],
        }
        for row in selected
    ]

    manifest = [
        {
            "id": row["id"],
            "filename": row["filename"],
            "md5": row["md5"],
            "size": row["size"],
            "state": row["state"],
        }
        for row in selected
    ]

    write_csv(
        ANNOTATIONS_DIR / "cbioportal_msi_scores.csv",
        sorted(msi_rows, key=lambda r: r["sample_id"]),
        ["sample_id", "patient", "msi_score_mantis", "msi_sensor_score", "msi_status", "label_source"],
    )
    write_csv(
        ANNOTATIONS_DIR / "selected_open_tcga_crc_slides.csv",
        selected,
        [
            "slide",
            "patient",
            "msi_status",
            "site",
            "fold",
            "project",
            "sample_type",
            "id",
            "filename",
            "md5",
            "size",
            "state",
            "msi_score_mantis",
            "msi_sensor_score",
            "label_source",
        ],
    )
    write_csv(
        ANNOTATIONS_DIR / "tcga_crc_msi_annotations.csv",
        annotations,
        [
            "slide",
            "patient",
            "msi_status",
            "site",
            "fold",
            "project",
            "gdc_file_id",
            "gdc_filename",
            "msi_score_mantis",
            "msi_sensor_score",
            "label_source",
        ],
    )
    write_csv(
        ANNOTATIONS_DIR / "gdc_manifest_tcga_crc_msi.tsv",
        manifest,
        ["id", "filename", "md5", "size", "state"],
        delimiter="\t",
    )

    counts = defaultdict(int)
    for row in selected:
        counts[row["msi_status"]] += 1
    print(f"Selected slides: {dict(counts)}")
    print(f"Wrote {ANNOTATIONS_DIR / 'tcga_crc_msi_annotations.csv'}")
    print(f"Wrote {ANNOTATIONS_DIR / 'gdc_manifest_tcga_crc_msi.tsv'}")
    print("Download slides with:")
    print(
        "gdc-client download "
        f"-m {ANNOTATIONS_DIR / 'gdc_manifest_tcga_crc_msi.tsv'} "
        f"-d {PROJECT_DIR / 'slideflow_project' / 'data' / 'slides'}"
    )


if __name__ == "__main__":
    main()
