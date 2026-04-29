import json
import math
import os
import random
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from ..database import models
from ..database.setup import SessionLocal
from ..services.dataset_sources import resolve_local_dataset_path

DATA_DIR = "/data"
DEFAULT_DATASET_PATH = r"E:\4basecare-MSI\datasets\CRC-VAL-HE-7K"

try:
    from PIL import Image
    import torch
    from sklearn.metrics import accuracy_score, classification_report, f1_score, roc_auc_score
    from torch import nn
    from torch.utils.data import DataLoader, Dataset, random_split
    from torchvision import transforms
    from torchvision.models import (
        ResNet18_Weights,
        ResNet34_Weights,
        ResNet50_Weights,
        resnet18,
        resnet34,
        resnet50,
    )
except ImportError:
    Image = None
    torch = None
    accuracy_score = None
    classification_report = None
    f1_score = None
    roc_auc_score = None
    nn = None
    DataLoader = None
    Dataset = None
    random_split = None
    transforms = None
    ResNet18_Weights = None
    ResNet34_Weights = None
    ResNet50_Weights = None
    resnet18 = None
    resnet34 = None
    resnet50 = None


BACKBONES = {
    "resnet18": (resnet18, ResNet18_Weights),
    "resnet34": (resnet34, ResNet34_Weights),
    "resnet50": (resnet50, ResNet50_Weights),
}


def _set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    if torch is not None:
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)


if Dataset is not None:
    class TifFolderDataset(Dataset):
        def __init__(
            self,
            root_dir: str,
            image_size: int,
            max_samples_per_class: int | None = None,
        ) -> None:
            if Image is None or transforms is None:
                raise RuntimeError(
                    "Training dependencies are missing. Install torch, torchvision, "
                    "Pillow, and scikit-learn."
                )

            self.root_dir = Path(root_dir)
            if not self.root_dir.exists():
                raise FileNotFoundError(f"Dataset path not found: {self.root_dir}")

            self.classes = sorted(
                [entry.name for entry in self.root_dir.iterdir() if entry.is_dir()]
            )
            if not self.classes:
                raise ValueError(f"No class directories found under {self.root_dir}")

            self.class_to_idx = {name: idx for idx, name in enumerate(self.classes)}
            self.samples: list[tuple[Path, int]] = []

            for class_name in self.classes:
                class_dir = self.root_dir / class_name
                files = sorted(
                    [
                        path
                        for path in class_dir.iterdir()
                        if path.is_file() and path.suffix.lower() in {".tif", ".tiff", ".png", ".jpg", ".jpeg"}
                    ]
                )
                if max_samples_per_class is not None:
                    files = files[:max_samples_per_class]
                self.samples.extend((path, self.class_to_idx[class_name]) for path in files)

            if not self.samples:
                raise ValueError(f"No image files found under {self.root_dir}")

            self.transform = transforms.Compose(
                [
                    transforms.Resize((image_size, image_size)),
                    transforms.RandomHorizontalFlip(),
                    transforms.RandomVerticalFlip(),
                    transforms.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.15),
                    transforms.ToTensor(),
                    transforms.Normalize(
                        mean=(0.485, 0.456, 0.406),
                        std=(0.229, 0.224, 0.225),
                    ),
                ]
            )

        def __len__(self) -> int:
            return len(self.samples)

        def __getitem__(self, index: int) -> tuple[Any, int]:
            image_path, label = self.samples[index]
            image = Image.open(image_path).convert("RGB")
            return self.transform(image), label
else:
    class TifFolderDataset:  # pragma: no cover - import guard fallback
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise RuntimeError(
                "Training dependencies are missing. Install torch, torchvision, "
                "Pillow, and scikit-learn."
            )


def _build_model(backbone: str, num_classes: int, use_pretrained: bool) -> Any:
    backbone_entry = BACKBONES.get(backbone)
    if backbone_entry is None or backbone_entry[0] is None:
        supported = ", ".join(
            sorted(name for name, entry in BACKBONES.items() if entry[0] is not None)
        )
        raise ValueError(f"Unsupported backbone '{backbone}'. Supported backbones: {supported}")

    builder, weights_enum = backbone_entry
    weights = weights_enum.DEFAULT if use_pretrained and weights_enum is not None else None
    model = builder(weights=weights)
    in_features = model.fc.in_features
    model.fc = nn.Linear(in_features, num_classes)
    return model


def _dataset_summary(dataset: TifFolderDataset) -> dict[str, int]:
    counts = Counter()
    for _, label in dataset.samples:
        counts[dataset.classes[label]] += 1
    return dict(sorted(counts.items()))


def _update_experiment(
    exp_id: str,
    *,
    status: str,
    metrics: dict[str, Any] | None = None,
) -> None:
    db = SessionLocal()
    try:
        exp = (
            db.query(models.Experiment)
            .filter(models.Experiment.experiment_id == exp_id)
            .first()
        )
        if exp:
            exp.status = status
            if metrics is not None:
                exp.metrics = metrics
            db.commit()
    finally:
        db.close()


def run_patch_training(exp_id: str, config_req: dict[str, Any]) -> None:
    dataset_path = resolve_local_dataset_path(config_req)
    output_root = config_req.get("output_dir") or os.path.join(DATA_DIR, "patch_models")
    run_dir = os.path.join(output_root, exp_id)
    os.makedirs(run_dir, exist_ok=True)

    try:
        if torch is None:
            raise RuntimeError(
                "Patch training requires torch, torchvision, Pillow, scikit-learn, "
                "and numpy to be installed."
            )
        if dataset_path.startswith("gs://"):
            raise RuntimeError(
                "Google bucket datasets must be staged on the VM triad runner before training."
            )

        seed = int(config_req.get("seed", 310))
        _set_seed(seed)

        dataset = TifFolderDataset(
            root_dir=dataset_path,
            image_size=int(config_req.get("image_size", 224)),
            max_samples_per_class=config_req.get("max_samples_per_class"),
        )

        val_split = float(config_req.get("val_split", 0.2))
        val_size = max(1, int(len(dataset) * val_split))
        train_size = len(dataset) - val_size
        if train_size <= 0:
            raise ValueError("Validation split leaves no training samples.")

        generator = torch.Generator().manual_seed(seed)
        train_dataset, val_dataset = random_split(
            dataset, [train_size, val_size], generator=generator
        )

        batch_size = int(config_req.get("batch_size", 32))
        num_workers = int(config_req.get("num_workers", 0))
        train_loader = DataLoader(
            train_dataset,
            batch_size=batch_size,
            shuffle=True,
            num_workers=num_workers,
        )
        val_loader = DataLoader(
            val_dataset,
            batch_size=batch_size,
            shuffle=False,
            num_workers=num_workers,
        )

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = _build_model(
            backbone=config_req.get("backbone", "resnet18"),
            num_classes=len(dataset.classes),
            use_pretrained=bool(config_req.get("use_pretrained", True)),
        ).to(device)

        optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=float(config_req.get("learning_rate", 1e-4)),
        )
        criterion = nn.CrossEntropyLoss()

        epochs = int(config_req.get("epochs", 10))
        best_val_acc = -math.inf
        history: list[dict[str, float]] = []
        best_state_path = os.path.join(run_dir, "best_model.pt")

        for epoch_idx in range(epochs):
            model.train()
            train_loss_sum = 0.0
            train_items = 0

            for images, labels in train_loader:
                images = images.to(device)
                labels = labels.to(device)

                optimizer.zero_grad()
                logits = model(images)
                loss = criterion(logits, labels)
                loss.backward()
                optimizer.step()

                batch_items = labels.size(0)
                train_loss_sum += loss.item() * batch_items
                train_items += batch_items

            model.eval()
            val_loss_sum = 0.0
            val_items = 0
            y_true: list[int] = []
            y_pred: list[int] = []
            y_prob: list[list[float]] = []

            with torch.no_grad():
                for images, labels in val_loader:
                    images = images.to(device)
                    labels = labels.to(device)
                    logits = model(images)
                    loss = criterion(logits, labels)
                    probs = torch.softmax(logits, dim=1)
                    preds = torch.argmax(probs, dim=1)

                    batch_items = labels.size(0)
                    val_loss_sum += loss.item() * batch_items
                    val_items += batch_items
                    y_true.extend(labels.cpu().tolist())
                    y_pred.extend(preds.cpu().tolist())
                    y_prob.extend(probs.cpu().tolist())

            train_loss = train_loss_sum / max(train_items, 1)
            val_loss = val_loss_sum / max(val_items, 1)
            val_acc = float(accuracy_score(y_true, y_pred))
            val_f1 = float(f1_score(y_true, y_pred, average="macro"))

            history.append(
                {
                    "epoch": float(epoch_idx + 1),
                    "train_loss": train_loss,
                    "val_loss": val_loss,
                    "val_accuracy": val_acc,
                    "val_f1_macro": val_f1,
                }
            )

            if val_acc > best_val_acc:
                best_val_acc = val_acc
                torch.save(model.state_dict(), best_state_path)

        multiclass_auc = None
        if len(set(y_true)) > 1:
            try:
                multiclass_auc = float(
                    roc_auc_score(
                        y_true,
                        np.array(y_prob),
                        multi_class="ovr",
                        average="macro",
                    )
                )
            except ValueError:
                multiclass_auc = None

        report = classification_report(
            y_true,
            y_pred,
            target_names=dataset.classes,
            output_dict=True,
            zero_division=0,
        )

        summary = {
            "experiment_id": exp_id,
            "experiment_name": config_req.get("experiment_name", exp_id),
            "approach_label": config_req.get("approach_label", "Approach2"),
            "training_mode": config_req.get("training_mode", "patch_classification"),
            "seed": seed,
            "dataset_path": dataset_path,
            "class_names": dataset.classes,
            "class_distribution": _dataset_summary(dataset),
            "total_images": len(dataset),
            "train_images": train_size,
            "val_images": val_size,
            "epochs": epochs,
            "batch_size": batch_size,
            "backbone": config_req.get("backbone", "resnet18"),
            "best_val_accuracy": best_val_acc,
            "final_val_f1_macro": float(history[-1]["val_f1_macro"]),
            "val_auroc_ovr_macro": multiclass_auc,
            "history": history,
            "classification_report": report,
            "artifacts": {
                "model_path": best_state_path,
                "metrics_path": os.path.join(run_dir, "metrics.json"),
            },
        }

        with open(os.path.join(run_dir, "metrics.json"), "w", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=2)

        _update_experiment(exp_id, status="completed", metrics=summary)
    except Exception as exc:
        _update_experiment(
            exp_id,
            status="failed",
            metrics={"error": str(exc), "dataset_path": dataset_path},
        )
