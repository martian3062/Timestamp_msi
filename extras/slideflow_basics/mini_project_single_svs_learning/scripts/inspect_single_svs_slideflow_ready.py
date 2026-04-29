import argparse
import csv
import json
from pathlib import Path

from openslide import OpenSlide


def read_manifest(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect whether a single SVS is ready for simple Slideflow exploration.")
    parser.add_argument("--slide", required=True, help="Path to the .svs slide")
    parser.add_argument("--manifest", help="Optional one-row manifest created by the prepare script")
    args = parser.parse_args()

    slide_path = Path(args.slide).expanduser().resolve()
    slide = OpenSlide(str(slide_path))

    manifest_rows = []
    if args.manifest:
        manifest_rows = read_manifest(Path(args.manifest).expanduser().resolve())

    try:
        import slideflow as sf  # type: ignore

        slideflow_info = {
            "installed": True,
            "version": getattr(sf, "__version__", "unknown"),
            "studio_command": "slideflow-studio",
            "module_command": "python -m slideflow.studio",
        }
    except Exception as exc:  # pragma: no cover - depends on environment
        slideflow_info = {
            "installed": False,
            "error": str(exc),
            "studio_command": "slideflow-studio",
            "module_command": "python -m slideflow.studio",
        }

    report = {
        "slide_name": slide_path.name,
        "dimensions": list(slide.dimensions),
        "level_count": slide.level_count,
        "level_dimensions": [list(level) for level in slide.level_dimensions],
        "manifest_rows": len(manifest_rows),
        "manifest_preview": manifest_rows[:1],
        "slideflow": slideflow_info,
        "next_steps": [
            "Review thumbnail and tissue overlay outputs from the prepare script.",
            "Open Slideflow Studio if GUI display is available.",
            "Use the manifest as a lightweight reference while exploring the slide.",
        ],
    }

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
