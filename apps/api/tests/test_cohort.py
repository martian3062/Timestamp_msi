from app.models.cohort import CohortValidationRequest, UploadedTextFile
from app.services.cohort import parse_delimited, validate_cohort


def test_parse_delimited_handles_csv_quotes() -> None:
    rows, columns = parse_delimited(
        'patient_id,slide_filename,msi_label,fold\n'
        'TCGA-1,"slide, one.svs",MSI-H,0\n'
        'TCGA-2,slide-two.svs,MSS,1\n'
    )

    assert columns == ["patient_id", "slide_filename", "msi_label", "fold"]
    assert rows[0]["slide_filename"] == "slide, one.svs"
    assert rows[1]["msi_label"] == "MSS"


def test_validate_cohort_detects_required_fields_and_counts() -> None:
    response = validate_cohort(
        CohortValidationRequest(
            annotations=UploadedTextFile(
                name="annotations.csv",
                contents=(
                    "patient_id,slide_filename,msi_label,fold\n"
                    "TCGA-1,a.svs,MSI-H,0\n"
                    "TCGA-2,b.svs,MSS,0\n"
                    "TCGA-3,c.svs,MSS,1\n"
                ),
            ),
            manifest=UploadedTextFile(
                name="manifest.tsv",
                contents="id\tfilename\nuuid-1\ta.svs\nuuid-2\tb.svs\n",
            ),
        )
    )

    assert response.ready_for_vm is True
    assert response.label_counts == {"MSI-H": 1, "MSS": 2}
    assert response.fold_counts == {"0": 2, "1": 1}
    assert response.annotations is not None
    assert response.annotations.mapping.patient == "patient_id"
    assert response.manifest is not None
    assert response.manifest.mapping.filename == "filename"


def test_validate_cohort_reports_missing_fields() -> None:
    response = validate_cohort(
        CohortValidationRequest(
            annotations=UploadedTextFile(
                name="bad.csv",
                contents="sample,value\nA,1\n",
            )
        )
    )

    assert response.ready_for_vm is False
    assert response.annotations is not None
    assert response.annotations.missing_required == [
        "patient",
        "slide",
        "label",
        "fold",
    ]

