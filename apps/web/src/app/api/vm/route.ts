import { execFile, spawn } from "node:child_process";
import { homedir } from "node:os";
import path from "node:path";
import { promisify } from "node:util";
import { NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const execFileAsync = promisify(execFile);

const vmConfig = {
  user: process.env.MSI_VM_USER ?? "pardeep",
  host: process.env.MSI_VM_HOST ?? "34.55.157.128",
  keyPath:
    process.env.MSI_VM_KEY ??
    path.join(homedir(), ".ssh", "evolet_rsa"),
  projectRoot:
    process.env.MSI_VM_PROJECT_ROOT ??
    "/home/pardeep/pathology310_projects/single_slide_morphology/project_1_slideflow_msi_tcga_crc",
};

const allowedBrowseRoots = [
  vmConfig.projectRoot,
  `${vmConfig.projectRoot}/annotations`,
  `${vmConfig.projectRoot}/scripts`,
  `${vmConfig.projectRoot}/slideflow_project`,
  `${vmConfig.projectRoot}/slideflow_project/data`,
  `${vmConfig.projectRoot}/slideflow_project/data/slides`,
];

type VmAction =
  | "status"
  | "listFiles"
  | "uploadFile"
  | "startDownloader"
  | "startJupyter"
  | "startTunnel";

type UploadKind = "annotations" | "manifest";

function sshBaseArgs() {
  return [
    "-i",
    vmConfig.keyPath,
    "-o",
    "BatchMode=yes",
    "-o",
    "ConnectTimeout=12",
    "-o",
    "ServerAliveInterval=30",
    "-o",
    "ServerAliveCountMax=3",
    `${vmConfig.user}@${vmConfig.host}`,
  ];
}

function shellQuote(value: string) {
  return `'${value.replace(/'/g, `'\\''`)}'`;
}

function isAllowedPath(value: string) {
  const normalized = value.replace(/\/+$/, "");

  return allowedBrowseRoots.some((root) => {
    const cleanRoot = root.replace(/\/+$/, "");
    return normalized === cleanRoot || normalized.startsWith(`${cleanRoot}/`);
  });
}

async function runSsh(command: string, timeout = 30000) {
  const { stdout, stderr } = await execFileAsync("ssh", [...sshBaseArgs(), command], {
    maxBuffer: 1024 * 1024 * 4,
    timeout,
    windowsHide: true,
  });

  return {
    stdout: stdout.trim(),
    stderr: stderr.trim(),
  };
}

async function runSshWithInput(command: string, input: string, timeout = 30000) {
  return new Promise<{ stdout: string; stderr: string }>((resolve, reject) => {
    const child = spawn("ssh", [...sshBaseArgs(), command], {
      windowsHide: true,
    });
    const timer = setTimeout(() => {
      child.kill();
      reject(new Error("SSH upload timed out."));
    }, timeout);
    const stdout: Buffer[] = [];
    const stderr: Buffer[] = [];

    child.stdout.on("data", (chunk: Buffer) => stdout.push(chunk));
    child.stderr.on("data", (chunk: Buffer) => stderr.push(chunk));
    child.on("error", (error) => {
      clearTimeout(timer);
      reject(error);
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      const result = {
        stdout: Buffer.concat(stdout).toString("utf8").trim(),
        stderr: Buffer.concat(stderr).toString("utf8").trim(),
      };

      if (code === 0) {
        resolve(result);
        return;
      }

      reject(
        new Error(
          result.stderr || result.stdout || `SSH command failed with code ${code}`,
        ),
      );
    });

    child.stdin.end(input);
  });
}

async function startLocalTunnel() {
  const args = [
    "-i",
    vmConfig.keyPath,
    "-N",
    "-L",
    "8888:127.0.0.1:8888",
    "-o",
    "ExitOnForwardFailure=yes",
    "-o",
    "ServerAliveInterval=30",
    "-o",
    "ServerAliveCountMax=6",
    `${vmConfig.user}@${vmConfig.host}`,
  ];

  const child = spawn("ssh", args, {
    detached: true,
    stdio: "ignore",
    windowsHide: true,
  });

  child.unref();

  return {
    stdout:
      "Tunnel requested on http://127.0.0.1:8888. If it was already open, keep using the same local link.",
    stderr: "",
  };
}

function uploadTarget(kind: UploadKind) {
  if (kind === "annotations") {
    return `${vmConfig.projectRoot}/annotations/tcga_crc_msi_annotations.csv`;
  }

  return `${vmConfig.projectRoot}/annotations/gdc_manifest_tcga_crc_msi.tsv`;
}

function statusCommand() {
  return `
set -e
echo "VM: $(hostname)"
echo "User: $(whoami)"
echo "Project: ${vmConfig.projectRoot}"
echo
echo "[GPU]"
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv,noheader
else
  echo "nvidia-smi not found"
fi
echo
echo "[Disk]"
df -h ${shellQuote(vmConfig.projectRoot)} | tail -n 1
echo
echo "[Slides]"
SLIDE_DIR=${shellQuote(`${vmConfig.projectRoot}/slideflow_project/data/slides`)}
mkdir -p "$SLIDE_DIR"
echo "svs=$(find "$SLIDE_DIR" -maxdepth 1 -name '*.svs' | wc -l)"
echo "partial=$(find "$SLIDE_DIR" -maxdepth 1 -name '*.part' | wc -l)"
du -sh "$SLIDE_DIR" 2>/dev/null || true
echo
echo "[Processes]"
ps -eo pid,args | awk '/download_gdc_manifest.py|jupyter-lab/ && !/awk/ {print}' || echo "no downloader or jupyter process"
`;
}

function downloaderCommand() {
  return `
set -e
cd ${shellQuote(vmConfig.projectRoot)}
mkdir -p logs slideflow_project/data/slides
if ps -eo args | awk '/download_gdc_manifest.py/ && !/awk/ {found=1} END {exit !found}'; then
  echo "Downloader already running"
else
  nohup pathology310-run python scripts/download_gdc_manifest.py --manifest annotations/gdc_manifest_tcga_crc_msi.tsv --out slideflow_project/data/slides > logs/gdc_download.log 2>&1 &
  echo "Downloader started"
fi
sleep 1
ps -eo pid,args | awk '/download_gdc_manifest.py/ && !/awk/ {print}' || true
tail -n 20 logs/gdc_download.log 2>/dev/null || true
`;
}

function jupyterCommand() {
  return `
set -e
mkdir -p ${shellQuote(`${vmConfig.projectRoot}/logs`)}
if ps -eo args | awk '/jupyter-lab/ && /8888/ && !/awk/ {found=1} END {exit !found}'; then
  echo "Jupyter already running on VM port 8888"
else
  cd ${shellQuote(vmConfig.projectRoot)}
  nohup pathology310-run jupyter lab --ip 127.0.0.1 --port 8888 --no-browser > logs/jupyter.log 2>&1 &
  echo "Jupyter started on VM port 8888"
fi
sleep 2
ps -eo pid,args | awk '/jupyter-lab/ && /8888/ && !/awk/ {print}' || true
grep -Eo 'http://127.0.0.1:8888/[^ ]+' logs/jupyter.log 2>/dev/null | tail -n 1 || true
`;
}

export async function GET() {
  return NextResponse.json({
    ok: true,
    vm: {
      user: vmConfig.user,
      host: vmConfig.host,
      projectRoot: vmConfig.projectRoot,
      keyPath: vmConfig.keyPath,
    },
    actions: ["status", "listFiles", "startDownloader", "startJupyter", "startTunnel"],
  });
}

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as {
      action?: VmAction;
      path?: string;
      kind?: UploadKind;
      contents?: string;
    };
    const action = body.action;

    if (!action) {
      return NextResponse.json(
        { ok: false, error: "Missing VM action." },
        { status: 400 },
      );
    }

    if (action === "status") {
      const result = await runSsh(statusCommand(), 45000);
      return NextResponse.json({ ok: true, action, ...result });
    }

    if (action === "listFiles") {
      const browsePath = body.path || vmConfig.projectRoot;

      if (!isAllowedPath(browsePath)) {
        return NextResponse.json(
          { ok: false, error: "Path is outside the configured project roots." },
          { status: 400 },
        );
      }

      const result = await runSsh(
        `find ${shellQuote(browsePath)} -maxdepth 1 -printf '%y\\t%f\\t%s\\t%TY-%Tm-%Td %TH:%TM\\n' | sort`,
      );

      return NextResponse.json({ ok: true, action, path: browsePath, ...result });
    }

    if (action === "uploadFile") {
      if (!body.kind || !body.contents) {
        return NextResponse.json(
          { ok: false, error: "Upload requires kind and contents." },
          { status: 400 },
        );
      }

      const target = uploadTarget(body.kind);
      const command = `mkdir -p ${shellQuote(`${vmConfig.projectRoot}/annotations`)} && cat > ${shellQuote(target)} && wc -l ${shellQuote(target)}`;
      const result = await runSshWithInput(command, body.contents, 45000);

      return NextResponse.json({ ok: true, action, path: target, ...result });
    }

    if (action === "startDownloader") {
      const result = await runSsh(downloaderCommand(), 45000);
      return NextResponse.json({ ok: true, action, ...result });
    }

    if (action === "startJupyter") {
      const result = await runSsh(jupyterCommand(), 45000);
      return NextResponse.json({ ok: true, action, ...result });
    }

    if (action === "startTunnel") {
      const result = await startLocalTunnel();
      return NextResponse.json({ ok: true, action, ...result });
    }

    return NextResponse.json(
      { ok: false, error: `Unsupported VM action: ${action}` },
      { status: 400 },
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown VM error";

    return NextResponse.json(
      { ok: false, error: message },
      { status: 500 },
    );
  }
}
