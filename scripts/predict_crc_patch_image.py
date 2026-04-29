import argparse
import json
from pathlib import Path

import torch
from PIL import Image
from torch import nn
from torchvision import transforms
from torchvision.models import ResNet18_Weights, ResNet34_Weights, ResNet50_Weights
from torchvision.models import resnet18, resnet34, resnet50


BACKBONES = {
    "resnet18": (resnet18, ResNet18_Weights),
    "resnet34": (resnet34, ResNet34_Weights),
    "resnet50": (resnet50, ResNet50_Weights),
}


def build_model(backbone: str, num_classes: int) -> nn.Module:
    builder, _weights_enum = BACKBONES[backbone]
    model = builder(weights=None)
    model.fc = nn.Linear(model.fc.in_features, num_classes)
    return model


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict one CRC patch image.")
    parser.add_argument("--image-path", required=True)
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--dataset-path", required=True)
    parser.add_argument("--backbone", default="resnet18", choices=sorted(BACKBONES))
    parser.add_argument("--image-size", type=int, default=224)
    args = parser.parse_args()

    dataset_root = Path(args.dataset_path)
    class_names = sorted([entry.name for entry in dataset_root.iterdir() if entry.is_dir()])
    if not class_names:
        raise ValueError(f"No class folders found under {dataset_root}")

    image_path = Path(args.image_path)
    model_path = Path(args.model_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")

    transform = transforms.Compose(
        [
            transforms.Resize((args.image_size, args.image_size)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=(0.485, 0.456, 0.406),
                std=(0.229, 0.224, 0.225),
            ),
        ]
    )

    image = Image.open(image_path).convert("RGB")
    tensor = transform(image).unsqueeze(0)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = build_model(args.backbone, len(class_names)).to(device)
    state_dict = torch.load(model_path, map_location=device)
    model.load_state_dict(state_dict)
    model.eval()

    with torch.no_grad():
        logits = model(tensor.to(device))
        probabilities = torch.softmax(logits, dim=1).cpu().tolist()[0]

    best_index = max(range(len(probabilities)), key=probabilities.__getitem__)
    payload = {
        "prediction": class_names[best_index],
        "probability": float(probabilities[best_index]),
        "probabilities": {
            class_name: float(probability)
            for class_name, probability in zip(class_names, probabilities)
        },
        "model_path": str(model_path),
    }
    print(json.dumps(payload), flush=True)


if __name__ == "__main__":
    main()
