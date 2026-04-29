import argparse
import json
import random
from collections import Counter
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from sklearn.metrics import accuracy_score, classification_report, f1_score, roc_auc_score
from torch import nn
from torch.utils.data import DataLoader, Dataset, random_split
from torchvision import transforms
from torchvision.models import ResNet18_Weights, ResNet34_Weights, ResNet50_Weights
from torchvision.models import resnet18, resnet34, resnet50


BACKBONES = {
    "resnet18": (resnet18, ResNet18_Weights),
    "resnet34": (resnet34, ResNet34_Weights),
    "resnet50": (resnet50, ResNet50_Weights),
}


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


class TifFolderDataset(Dataset):
    def __init__(self, root_dir: str, image_size: int, max_samples_per_class: int | None) -> None:
        self.root_dir = Path(root_dir)
        if not self.root_dir.exists():
            raise FileNotFoundError(f"Dataset path not found: {self.root_dir}")

        self.classes = sorted([entry.name for entry in self.root_dir.iterdir() if entry.is_dir()])
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

    def __getitem__(self, index: int) -> tuple[torch.Tensor, int]:
        image_path, label = self.samples[index]
        image = Image.open(image_path).convert("RGB")
        return self.transform(image), label


def build_model(backbone: str, num_classes: int, use_pretrained: bool) -> nn.Module:
    backbone_entry = BACKBONES.get(backbone)
    if backbone_entry is None:
        supported = ", ".join(sorted(BACKBONES))
        raise ValueError(f"Unsupported backbone '{backbone}'. Supported backbones: {supported}")
    builder, weights_enum = backbone_entry
    weights = weights_enum.DEFAULT if use_pretrained else None
    model = builder(weights=weights)
    in_features = model.fc.in_features
    model.fc = nn.Linear(in_features, num_classes)
    return model


def dataset_summary(dataset: TifFolderDataset) -> dict[str, int]:
    counts = Counter()
    for _, label in dataset.samples:
        counts[dataset.classes[label]] += 1
    return dict(sorted(counts.items()))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def train(args: argparse.Namespace) -> None:
    set_seed(args.seed)

    run_dir = Path(args.output_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = run_dir / "metrics.json"
    status_path = run_dir / "status.json"
    best_model_path = run_dir / "best_model.pt"

    dataset = TifFolderDataset(args.dataset_path, args.image_size, args.max_samples_per_class)
    val_size = max(1, int(len(dataset) * args.val_split))
    train_size = len(dataset) - val_size
    if train_size <= 0:
        raise ValueError("Validation split leaves no training samples.")

    generator = torch.Generator().manual_seed(args.seed)
    train_dataset, val_dataset = random_split(dataset, [train_size, val_size], generator=generator)

    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = build_model(args.backbone, len(dataset.classes), args.use_pretrained).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)
    criterion = nn.CrossEntropyLoss()

    history: list[dict[str, float]] = []
    best_val_accuracy = -1.0
    last_probs: np.ndarray | None = None
    last_true: list[int] = []
    last_pred: list[int] = []

    write_json(
        status_path,
        {
            "status": "running",
            "dataset_path": args.dataset_path,
            "device": str(device),
            "epochs_total": args.epochs,
            "epochs_completed": 0,
        },
    )

    for epoch_idx in range(args.epochs):
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
        val_accuracy = float(accuracy_score(y_true, y_pred))
        val_f1_macro = float(f1_score(y_true, y_pred, average="macro"))

        epoch_metrics = {
            "epoch": epoch_idx + 1,
            "train_loss": train_loss,
            "val_loss": val_loss,
            "val_accuracy": val_accuracy,
            "val_f1_macro": val_f1_macro,
        }
        history.append(epoch_metrics)
        last_probs = np.array(y_prob)
        last_true = y_true
        last_pred = y_pred

        if val_accuracy > best_val_accuracy:
            best_val_accuracy = val_accuracy
            torch.save(model.state_dict(), best_model_path)

        write_json(
            status_path,
            {
                "status": "running",
                "dataset_path": args.dataset_path,
                "device": str(device),
                "epochs_total": args.epochs,
                "epochs_completed": epoch_idx + 1,
                "latest_epoch": epoch_metrics,
                "best_val_accuracy": best_val_accuracy,
                "history": history,
            },
        )

    multiclass_auc = None
    if last_probs is not None and len(set(last_true)) > 1:
        try:
            multiclass_auc = float(
                roc_auc_score(
                    last_true,
                    last_probs,
                    multi_class="ovr",
                    average="macro",
                )
            )
        except ValueError:
            multiclass_auc = None

    report = classification_report(
        last_true,
        last_pred,
        target_names=dataset.classes,
        output_dict=True,
        zero_division=0,
    )

    final_metrics = {
        "status": "completed",
        "dataset_path": args.dataset_path,
        "device": str(device),
        "class_names": dataset.classes,
        "class_distribution": dataset_summary(dataset),
        "total_images": len(dataset),
        "train_images": train_size,
        "val_images": val_size,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "backbone": args.backbone,
        "image_size": args.image_size,
        "learning_rate": args.learning_rate,
        "best_val_accuracy": best_val_accuracy,
        "final_val_f1_macro": float(history[-1]["val_f1_macro"]),
        "val_auroc_ovr_macro": multiclass_auc,
        "history": history,
        "classification_report": report,
        "artifacts": {
            "model_path": str(best_model_path),
            "metrics_path": str(metrics_path),
            "status_path": str(status_path),
        },
    }
    write_json(metrics_path, final_metrics)
    write_json(status_path, final_metrics)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train CRC-VAL-HE-7K patch classifier.")
    parser.add_argument("--dataset-path", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--backbone", default="resnet18", choices=sorted(BACKBONES))
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--image-size", type=int, default=224)
    parser.add_argument("--val-split", type=float, default=0.2)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--seed", type=int, default=310)
    parser.add_argument("--max-samples-per-class", type=int, default=None)
    parser.add_argument("--use-pretrained", action="store_true")
    return parser


if __name__ == "__main__":
    train(build_parser().parse_args())
