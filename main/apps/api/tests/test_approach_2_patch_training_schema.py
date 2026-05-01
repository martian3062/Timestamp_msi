from app.approach_2.schemas.schemas import TCGASlideTriadRequest, TrainMilRequest
from app.approach_2.services.dataset_sources import resolve_remote_dataset_path
from app.approach_2.services.triad_runtime import build_tcga_slide_triad_specs


def test_patch_training_request_accepts_folder_dataset_fields() -> None:
    request = TrainMilRequest(
        experiment_name="crc-val-he-7k-baseline",
        training_mode="patch_classification",
        dataset_path=r"E:\4basecare-MSI\datasets\CRC-VAL-HE-7K",
        backbone="resnet18",
        image_size=224,
        val_split=0.2,
    )

    assert request.training_mode == "patch_classification"
    assert request.dataset_path.endswith("CRC-VAL-HE-7K")
    assert request.backbone == "resnet18"


def test_patch_training_request_accepts_google_bucket_source() -> None:
    request = TrainMilRequest(
        experiment_name="crc-val-he-7k-gcs",
        training_mode="patch_classification",
        dataset_source="google_bucket",
        google_bucket_uri="gs://bucket-name/path/to/CRC-VAL-HE-7K",
    )

    assert request.dataset_source == "google_bucket"
    assert request.google_bucket_uri == "gs://bucket-name/path/to/CRC-VAL-HE-7K"


def test_google_bucket_remote_resolution_builds_stage_commands() -> None:
    dataset_path, commands = resolve_remote_dataset_path(
        {
            "dataset_source": "google_bucket",
            "google_bucket_uri": "gs://bucket-name/path/to/CRC-VAL-HE-7K",
        },
        "exp1234",
    )

    assert dataset_path.endswith("/datasets/staged_exp1234")
    assert any("gcloud storage rsync --recursive" in command for command in commands)
    assert any("gsutil -m rsync -r" in command for command in commands)


def test_tcga_slide_triad_request_and_specs_build_three_approaches() -> None:
    request = TCGASlideTriadRequest(
        experiment_name="tcga-coad-20",
        slide_limit=18,
        n_folds=3,
        bucket_uri="gs://wsi_aiml_repo/TCGA/TCGA_COAD/TCGA_COAD",
        feature_extractor="virchow,uni_v2,uni,phikon,ctranspath,resnet50_imagenet",
    )

    bundle_id, specs = build_tcga_slide_triad_specs(request.model_dump())

    assert bundle_id
    assert len(specs) == 3
    assert {spec["approach_label"] for spec in specs} == {"Approach1", "Approach2", "MonteCarlo"}
    assert all(spec["bundle_id"] == bundle_id for spec in specs)
    assert all(spec["training_mode"] == "mil" for spec in specs)
    assert all(spec["n_folds"] == 3 for spec in specs)
    assert all("virchow" in str(spec["feature_extractor"]) for spec in specs)
