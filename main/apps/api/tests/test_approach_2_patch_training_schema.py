from app.approach_2.schemas.schemas import TrainMilRequest
from app.approach_2.services.dataset_sources import resolve_remote_dataset_path


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
