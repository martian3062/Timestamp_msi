import subprocess
from pathlib import PurePosixPath

from app.core.config import Settings, get_settings
from app.models.vm import FileUploadRequest, VmActionResponse, VmFile, VmFilesResponse

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class VmService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def status(self) -> VmActionResponse:
        return self._run("status", self._status_command(), timeout=45)

    def list_files(self, path: str | None = None) -> VmFilesResponse:
        browse_path = path or self.settings.vm_project_root
        if not self._is_allowed_path(browse_path):
            raise ValueError("Path is outside the configured project roots.")

        command = (
            f"find {self._quote(browse_path)} -maxdepth 1 "
            "-printf '%y\\t%f\\t%s\\t%TY-%Tm-%Td %TH:%TM\\n' | sort"
        )
        result = self._run("listFiles", command)
        return VmFilesResponse(
            action="listFiles",
            stdout=result.stdout,
            stderr=result.stderr,
            path=browse_path,
            files=self._parse_files(result.stdout),
        )

    def upload_file(self, request: FileUploadRequest) -> VmActionResponse:
        target = self._upload_target(request.kind)
        command = (
            f"mkdir -p {self._quote(f'{self.settings.vm_project_root}/annotations')} "
            f"&& cat > {self._quote(target)} && wc -l {self._quote(target)}"
        )
        return self._run("uploadFile", command, input_text=request.contents, timeout=45)

    def start_downloader(self) -> VmActionResponse:
        return self._run("startDownloader", self._downloader_command(), timeout=45)

    def start_jupyter(self) -> VmActionResponse:
        return self._run("startJupyter", self._jupyter_command(), timeout=45)

    def start_tunnel(self) -> VmActionResponse:
        args = [
            "ssh",
            "-i",
            str(self.settings.vm_key),
            "-N",
            "-L",
            (
                f"{self.settings.local_jupyter_port}:127.0.0.1:"
                f"{self.settings.vm_jupyter_port}"
            ),
            "-o",
            "ExitOnForwardFailure=yes",
            "-o",
            "ServerAliveInterval=30",
            "-o",
            "ServerAliveCountMax=6",
            self._target,
        ]
        subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
        )
        return VmActionResponse(
            action="startTunnel",
            stdout=(
                "Tunnel requested on "
                f"http://127.0.0.1:{self.settings.local_jupyter_port}."
            ),
        )

    def prepare_monte_carlo_workspace(self) -> VmActionResponse:
        return self._run("prepareMonteCarloWorkspace", self._monte_carlo_workspace_command(), timeout=45)

    def project_path(self, relative_path: str) -> str:
        clean = self._clean_relative_path(relative_path)
        return f"{self.settings.vm_project_root.rstrip('/')}/{clean}"

    def write_project_file(
        self,
        relative_path: str,
        contents: str,
        action: str = "writeProjectFile",
        mode: str | None = None,
        timeout: int = 45,
    ) -> VmActionResponse:
        target = self.project_path(relative_path)
        command = (
            f"mkdir -p {self._quote(str(PurePosixPath(target).parent))} "
            f"&& cat > {self._quote(target)}"
        )
        if mode:
            command += f" && chmod {mode} {self._quote(target)}"
        command += f" && wc -c {self._quote(target)}"
        return self._run(action, command, input_text=contents, timeout=timeout)

    def run_project_command(
        self,
        action: str,
        command: str,
        timeout: int = 30,
    ) -> VmActionResponse:
        return self._run(
            action,
            f"cd {self._quote(self.settings.vm_project_root)} && {command}",
            timeout=timeout,
        )

    @property
    def _target(self) -> str:
        return f"{self.settings.vm_user}@{self.settings.vm_host}"

    def _ssh_args(self) -> list[str]:
        return [
            "ssh",
            "-i",
            str(self.settings.vm_key),
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=12",
            "-o",
            "ServerAliveInterval=30",
            "-o",
            "ServerAliveCountMax=3",
            self._target,
        ]

    def _run(
        self,
        action: str,
        command: str,
        input_text: str | None = None,
        timeout: int = 30,
    ) -> VmActionResponse:
        completed = subprocess.run(
            [*self._ssh_args(), command],
            input=input_text,
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=CREATE_NO_WINDOW,
        )

        return VmActionResponse(
            ok=completed.returncode == 0,
            action=action,
            stdout=completed.stdout.strip(),
            stderr=completed.stderr.strip(),
        )

    def _is_allowed_path(self, value: str) -> bool:
        normalized = value.rstrip("/")
        for root in self.settings.allowed_browse_roots:
            clean_root = root.rstrip("/")
            if normalized == clean_root or normalized.startswith(f"{clean_root}/"):
                return True
        return False

    @staticmethod
    def _clean_relative_path(value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Project file path must be a safe relative path.")
        clean = str(path).strip("/")
        if not clean:
            raise ValueError("Project file path cannot be empty.")
        return clean

    def _upload_target(self, kind: str) -> str:
        if kind == "annotations":
            return f"{self.settings.vm_project_root}/annotations/tcga_crc_msi_annotations.csv"
        return f"{self.settings.vm_project_root}/annotations/gdc_manifest_tcga_crc_msi.tsv"

    def _status_command(self) -> str:
        root = self.settings.vm_project_root
        slide_dir = f"{root}/slideflow_project/data/slides"
        return f"""
set -e
echo "VM: $(hostname)"
echo "User: $(whoami)"
echo "Project: {root}"
echo
echo "[GPU]"
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv,noheader
else
  echo "nvidia-smi not found"
fi
echo
echo "[Disk]"
df -h {self._quote(root)} | tail -n 1
echo
echo "[Slides]"
SLIDE_DIR={self._quote(slide_dir)}
mkdir -p "$SLIDE_DIR"
echo "svs=$(find "$SLIDE_DIR" -maxdepth 1 -name '*.svs' | wc -l)"
echo "partial=$(find "$SLIDE_DIR" -maxdepth 1 -name '*.part' | wc -l)"
du -sh "$SLIDE_DIR" 2>/dev/null || true
echo
echo "[Processes]"
ps -eo pid,args | awk '/download_gdc_manifest.py|jupyter-lab/ && !/awk/ {{print}}' || echo "no downloader or jupyter process"
"""

    def _downloader_command(self) -> str:
        root = self.settings.vm_project_root
        return f"""
set -e
cd {self._quote(root)}
mkdir -p logs slideflow_project/data/slides
if ps -eo args | awk '/download_gdc_manifest.py/ && !/awk/ {{found=1}} END {{exit !found}}'; then
  echo "Downloader already running"
else
  nohup pathology310-run python scripts/download_gdc_manifest.py --manifest annotations/gdc_manifest_tcga_crc_msi.tsv --out slideflow_project/data/slides > logs/gdc_download.log 2>&1 &
  echo "Downloader started"
fi
sleep 1
ps -eo pid,args | awk '/download_gdc_manifest.py/ && !/awk/ {{print}}' || true
tail -n 20 logs/gdc_download.log 2>/dev/null || true
"""

    def _jupyter_command(self) -> str:
        root = self.settings.vm_project_root
        port = self.settings.vm_jupyter_port
        return f"""
set -e
mkdir -p {self._quote(f'{root}/logs')}
if ps -eo args | awk '/jupyter-lab/ && /{port}/ && !/awk/ {{found=1}} END {{exit !found}}'; then
  echo "Jupyter already running on VM port {port}"
else
  cd {self._quote(root)}
  nohup pathology310-run jupyter lab --ip 127.0.0.1 --port {port} --no-browser > logs/jupyter.log 2>&1 &
  echo "Jupyter started on VM port {port}"
fi
sleep 2
ps -eo pid,args | awk '/jupyter-lab/ && /{port}/ && !/awk/ {{print}}' || true
grep -Eo 'http://127.0.0.1:{port}/[^ ]+' logs/jupyter.log 2>/dev/null | tail -n 1 || true
"""

    def _monte_carlo_workspace_command(self) -> str:
        root = self.settings.vm_project_root
        return f"""
set -e
cd {self._quote(root)}
mkdir -p models/huggingface_cache models/monte_carlo logs configs
cat > configs/ai_integrations.env.example <<'EOF'
MSI_HF_TOKEN=
MSI_GROQ_API_KEY=
MSI_ZERVE_API_KEY=
MSI_FIRECRAWL_API_KEY=
MSI_TINYFISH_API_KEY=
HF_HOME=$PWD/models/huggingface_cache
TRANSFORMERS_CACHE=$PWD/models/huggingface_cache
EOF
echo "Monte Carlo workspace prepared"
echo "Project: {root}"
echo "HF cache: {root}/models/huggingface_cache"
echo "MC models: {root}/models/monte_carlo"
find models -maxdepth 2 -type d | sort
"""

    @staticmethod
    def _quote(value: str) -> str:
        return "'" + value.replace("'", "'\\''") + "'"

    @staticmethod
    def _parse_files(output: str) -> list[VmFile]:
        files: list[VmFile] = []
        for line in output.splitlines():
            if not line.strip():
                continue
            file_type, name, size, modified = (line.split("\t") + ["", "", "", ""])[:4]
            files.append(
                VmFile(
                    type={
                        "d": "directory",
                        "f": "file",
                    }.get(file_type, "other"),
                    name=name,
                    size=int(size or 0),
                    modified=modified,
                )
            )
        return files
