import argparse
import csv
import json
from pathlib import Path

import numpy as np
from openslide import OpenSlide
from PIL import Image, ImageEnhance


def tissue_mask_from_thumbnail(image: Image.Image) -> np.ndarray:
    rgb = np.asarray(image.convert("RGB")).astype(np.uint8)
    bright = rgb.mean(axis=2)
    channel_spread = rgb.max(axis=2) - rgb.min(axis=2)
    # A lightweight tissue heuristic for beginner QC outputs.
    mask = (bright < 225) & (channel_spread > 12)
    return mask


def save_mask(mask: np.ndarray, path: Path) -> None:
    mask_image = Image.fromarray((mask.astype(np.uint8) * 255), mode="L")
    mask_image.save(path)


def save_overlay(base: Image.Image, mask: np.ndarray, path: Path) -> None:
    rgb = np.asarray(base.convert("RGB")).copy()
    rgb[mask] = (0.60 * rgb[mask] + 0.40 * np.array([40, 180, 255])).astype(np.uint8)
    Image.fromarray(rgb).save(path)


def build_summary(slide: OpenSlide, slide_path: Path, mask: np.ndarray, thumb_size: tuple[int, int]) -> dict:
    width, height = slide.dimensions
    tissue_fraction = float(mask.mean()) if mask.size else 0.0
    properties = dict(slide.properties)
    selected = {
        "openslide.vendor": properties.get("openslide.vendor"),
        "openslide.objective-power": properties.get("openslide.objective-power"),
        "openslide.mpp-x": properties.get("openslide.mpp-x"),
        "openslide.mpp-y": properties.get("openslide.mpp-y"),
        "aperio.AppMag": properties.get("aperio.AppMag"),
    }
    return {
        "slide_name": slide_path.name,
        "slide_path": str(slide_path),
        "width": width,
        "height": height,
        "level_count": slide.level_count,
        "level_dimensions": [list(level) for level in slide.level_dimensions],
        "thumbnail_width": thumb_size[0],
        "thumbnail_height": thumb_size[1],
        "tissue_fraction_estimate": round(tissue_fraction, 6),
        "selected_properties": selected,
    }


def write_manifest(slide_path: Path, output_dir: Path) -> Path:
    manifest_path = output_dir / "single_slide_manifest.csv"
    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["slide", "patient", "label", "source", "notes"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "slide": slide_path.name,
                "patient": slide_path.stem.split(".")[0],
                "label": "unknown",
                "source": "open_source_demo",
                "notes": "Single-slide learning manifest for Slideflow exploration.",
            }
        )
    return manifest_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare simple QC assets around one SVS slide.")
    parser.add_argument("--slide", required=True, help="Path to the source .svs file")
    parser.add_argument("--output-dir", required=True, help="Folder where learning artifacts will be written")
    parser.add_argument("--thumb-width", type=int, default=1600, help="Max thumbnail width")
    args = parser.parse_args()

    slide_path = Path(args.slide).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    slide = OpenSlide(str(slide_path))

    width, height = slide.dimensions
    aspect = height / max(width, 1)
    thumb_height = max(1, int(args.thumb_width * aspect))
    thumbnail = slide.get_thumbnail((args.thumb_width, thumb_height)).convert("RGB")

    enhanced = ImageEnhance.Color(thumbnail).enhance(1.25)
    enhanced = ImageEnhance.Contrast(enhanced).enhance(1.12)
    enhanced = ImageEnhance.Sharpness(enhanced).enhance(1.08)

    mask = tissue_mask_from_thumbnail(thumbnail)

    thumbnail_path = output_dir / "thumbnail.png"
    enhanced_path = output_dir / "enhanced_preview.png"
    mask_path = output_dir / "tissue_mask.png"
    overlay_path = output_dir / "tissue_overlay.png"
    summary_path = output_dir / "slide_summary.json"

    thumbnail.save(thumbnail_path)
    enhanced.save(enhanced_path)
    save_mask(mask, mask_path)
    save_overlay(thumbnail, mask, overlay_path)

    summary = build_summary(slide, slide_path, mask, thumbnail.size)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    manifest_path = write_manifest(slide_path, output_dir)

    print(json.dumps(
        {
            "slide": str(slide_path),
            "output_dir": str(output_dir),
            "thumbnail": str(thumbnail_path),
            "enhanced_preview": str(enhanced_path),
            "tissue_mask": str(mask_path),
            "tissue_overlay": str(overlay_path),
            "summary": str(summary_path),
            "manifest": str(manifest_path),
        },
        indent=2,
    ))


if __name__ == "__main__":
    main()
