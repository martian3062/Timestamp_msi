from app.approach_2.schemas.schemas import TrainMilRequest


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
