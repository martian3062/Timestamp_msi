import argparse
import json
import shutil
import subprocess
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Print or launch Slideflow Studio for the single-slide learning mini project.")
    parser.add_argument("--slide", required=True, help="Path to the source .svs file")
    parser.add_argument("--manifest", help="Optional manifest path from the prepare step")
    parser.add_argument("--run-local", action="store_true", help="Attempt to launch Slideflow Studio on this machine")
    args = parser.parse_args()

    slide_path = Path(args.slide).expanduser().resolve()
    manifest_path = Path(args.manifest).expanduser().resolve() if args.manifest else None

    studio_cmd = shutil.which("slideflow-studio")
    python_cmd = shutil.which("python") or "python"

    payload = {
        "slide": str(slide_path),
        "manifest": str(manifest_path) if manifest_path else "",
        "local_studio_available": bool(studio_cmd),
        "local_studio_command": studio_cmd or "slideflow-studio",
        "local_module_command": f"{python_cmd} -m slideflow.studio",
        "vm_setup": [
            "source /opt/miniforge3/etc/profile.d/conda.sh",
            "conda activate /opt/miniforge3/envs/pathology310",
            "slideflow-studio",
        ],
        "studio_learning_note": "Open the SVS file in Slideflow Studio and keep the manifest plus QC images beside it for learning.",
    }

    launched = False
    launch_error = ""
    if args.run_local:
        if studio_cmd:
            try:
                subprocess.Popen([studio_cmd])
                launched = True
            except Exception as exc:  # pragma: no cover - GUI launch is environment-specific
                launch_error = str(exc)
        else:
            launch_error = "slideflow-studio was not found on this machine."

    if args.run_local:
        payload["run_local_requested"] = True
        payload["run_local_launched"] = launched
        if launch_error:
            payload["run_local_error"] = launch_error

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
