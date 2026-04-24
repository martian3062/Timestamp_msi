"use client";

import { useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ClipboardList,
  Database,
  FileCheck2,
  FileText,
  FlaskConical,
  FolderOpen,
  HardDrive,
  Play,
  RefreshCw,
  Server,
  Terminal,
  Upload,
  UploadCloud,
} from "lucide-react";

type TableRow = Record<string, string>;

type UploadedTable = {
  name: string;
  rows: TableRow[];
  columns: string[];
  rawText: string;
};

type UploadKind = "annotations" | "manifest";

type VmFileRow = {
  type: string;
  name: string;
  size: string;
  modified: string;
};

const requiredAnnotationFields = ["patient", "slide", "label", "fold"];
const requiredManifestFields = ["id", "filename"];

const commandBlock = `# Linux VM shell
cd /home/pardeep/pathology310_projects/single_slide_morphology/project_1_slideflow_msi_tcga_crc
pathology310-run python scripts/download_gdc_manifest.py \\
  --manifest annotations/gdc_manifest_tcga_crc_msi.tsv \\
  --out slideflow_project/data/slides

# Jupyter / Antigravity kernel
pathology310-run jupyter lab --ip 127.0.0.1 --port 8888 --no-browser`;

const stageRows = [
  {
    name: "Source cohort",
    owner: "cBioPortal + GDC",
    detail: "TCGA-COAD/READ MSI labels and diagnostic SVS slide manifest",
    state: "Ready",
  },
  {
    name: "Slide acquisition",
    owner: "VM storage",
    detail: "SVS files stay on the remote slide volume.",
    state: "60 SVS",
  },
  {
    name: "Feature extraction",
    owner: "pathology310",
    detail: "Notebook starts with CUDA and runtime checks.",
    state: "Jupyter",
  },
  {
    name: "Slideflow training",
    owner: "MIL workflow",
    detail: "Patient-level folds protect against leakage.",
    state: "Queued",
  },
];

function parseDelimited(text: string): { rows: TableRow[]; columns: string[] } {
  const rows: string[][] = [];
  let field = "";
  let row: string[] = [];
  let quoted = false;

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    const next = text[index + 1];

    if (char === '"' && quoted && next === '"') {
      field += '"';
      index += 1;
      continue;
    }

    if (char === '"') {
      quoted = !quoted;
      continue;
    }

    if (!quoted && (char === "," || char === "\t")) {
      row.push(field.trim());
      field = "";
      continue;
    }

    if (!quoted && (char === "\n" || char === "\r")) {
      if (char === "\r" && next === "\n") {
        index += 1;
      }
      row.push(field.trim());
      if (row.some(Boolean)) {
        rows.push(row);
      }
      row = [];
      field = "";
      continue;
    }

    field += char;
  }

  row.push(field.trim());
  if (row.some(Boolean)) {
    rows.push(row);
  }

  const [header = [], ...body] = rows;
  const columns = header.map((column) => column.trim());
  const parsedRows = body.map((cells) =>
    columns.reduce<TableRow>((acc, column, index) => {
      acc[column] = cells[index]?.trim() ?? "";
      return acc;
    }, {}),
  );

  return { rows: parsedRows, columns };
}

function normalizeColumn(column: string) {
  return column.toLowerCase().replace(/[^a-z0-9]/g, "");
}

function findColumn(columns: string[], candidates: string[]) {
  const normalizedCandidates = candidates.map(normalizeColumn);
  return columns.find((column) =>
    normalizedCandidates.some((candidate) =>
      normalizeColumn(column).includes(candidate),
    ),
  );
}

function countBy(rows: TableRow[], column?: string) {
  if (!column) {
    return {};
  }

  return rows.reduce<Record<string, number>>((acc, row) => {
    const value = row[column]?.trim() || "Missing";
    acc[value] = (acc[value] ?? 0) + 1;
    return acc;
  }, {});
}

function fileLabel(file?: UploadedTable) {
  return file ? `${file.name} (${file.rows.length} rows)` : "No file selected";
}

function parseVmFiles(output: string): VmFileRow[] {
  return output
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [type = "", name = "", size = "", modified = ""] = line.split("\t");

      return { type, name, size, modified };
    });
}

export function MsiWorkbench() {
  const [annotations, setAnnotations] = useState<UploadedTable>();
  const [manifest, setManifest] = useState<UploadedTable>();
  const [activeCommand, setActiveCommand] = useState(commandBlock);
  const [vmBusy, setVmBusy] = useState<string>();
  const [vmOutput, setVmOutput] = useState("Run a VM check to see live status.");
  const [vmError, setVmError] = useState("");
  const [vmPath, setVmPath] = useState(
    "/home/pardeep/pathology310_projects/single_slide_morphology/project_1_slideflow_msi_tcga_crc",
  );
  const [vmFiles, setVmFiles] = useState<VmFileRow[]>([]);

  const annotationMap = useMemo(() => {
    const columns = annotations?.columns ?? [];

    return {
      patient: findColumn(columns, ["patient", "case", "submitter"]),
      slide: findColumn(columns, ["slide", "filename", "file", "image"]),
      label: findColumn(columns, ["msi", "label", "class", "status"]),
      fold: findColumn(columns, ["fold", "split"]),
    };
  }, [annotations]);

  const manifestMap = useMemo(() => {
    const columns = manifest?.columns ?? [];

    return {
      id: findColumn(columns, ["id", "uuid", "fileid"]),
      filename: findColumn(columns, ["filename", "file", "name"]),
    };
  }, [manifest]);

  const labelCounts = useMemo(
    () => countBy(annotations?.rows ?? [], annotationMap.label),
    [annotations, annotationMap.label],
  );

  const foldCounts = useMemo(
    () => countBy(annotations?.rows ?? [], annotationMap.fold),
    [annotations, annotationMap.fold],
  );

  const missingAnnotationFields = requiredAnnotationFields.filter(
    (field) => !annotationMap[field as keyof typeof annotationMap],
  );
  const missingManifestFields = requiredManifestFields.filter(
    (field) => !manifestMap[field as keyof typeof manifestMap],
  );

  async function handleFile(kind: UploadKind, file?: File) {
    if (!file) {
      return;
    }

    const text = await file.text();
    const table = parseDelimited(text);
    const payload = {
      name: file.name,
      rows: table.rows,
      columns: table.columns,
      rawText: text,
    };

    if (kind === "annotations") {
      setAnnotations(payload);
      return;
    }

    setManifest(payload);
  }

  const usableAnnotationRows = annotations?.rows.length ?? 0;
  const usableManifestRows = manifest?.rows.length ?? 0;
  const readyChecks =
    missingAnnotationFields.length === 0 &&
    missingManifestFields.length === 0 &&
    usableAnnotationRows > 0 &&
    usableManifestRows > 0;

  async function runVmAction(
    action:
      | "status"
      | "listFiles"
      | "uploadFile"
      | "startDownloader"
      | "startJupyter"
      | "startTunnel",
    payload: Record<string, string> = {},
  ) {
    setVmBusy(action);
    setVmError("");

    try {
      const response = await fetch("/api/vm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, ...payload }),
      });
      const data = (await response.json()) as {
        ok: boolean;
        stdout?: string;
        stderr?: string;
        error?: string;
        path?: string;
      };

      if (!response.ok || !data.ok) {
        throw new Error(data.error || "VM action failed.");
      }

      const output = [data.stdout, data.stderr].filter(Boolean).join("\n\n");
      setVmOutput(output || "Done.");

      if (action === "listFiles") {
        setVmFiles(parseVmFiles(data.stdout ?? ""));
        if (data.path) {
          setVmPath(data.path);
        }
      }
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Unable to reach VM route.";
      setVmError(message);
      setVmOutput("");
    } finally {
      setVmBusy(undefined);
    }
  }

  function uploadToVm(kind: UploadKind) {
    const file = kind === "annotations" ? annotations : manifest;

    if (!file) {
      setVmError(`Choose a ${kind} file first.`);
      return;
    }

    void runVmAction("uploadFile", {
      kind,
      contents: file.rawText,
    });
  }

  return (
    <main className="min-h-screen overflow-hidden bg-[#030908] text-[#eefdf7]">
      <div className="pointer-events-none fixed inset-0 bg-[linear-gradient(115deg,rgba(44,255,204,0.18),transparent_34%),linear-gradient(245deg,rgba(119,156,255,0.18),transparent_32%),radial-gradient(circle_at_50%_-10%,rgba(235,255,248,0.16),transparent_34%)]" />
      <div className="pointer-events-none fixed inset-0 bg-[linear-gradient(rgba(255,255,255,0.035)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.035)_1px,transparent_1px)] bg-[size:72px_72px] opacity-35" />

      <section className="relative mx-auto flex min-h-[92vh] w-full max-w-[1500px] flex-col px-4 pb-8 pt-4 sm:px-6 lg:px-8">
        <header className="flex min-h-14 items-center justify-between border-b border-white/10">
          <div className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-full border border-[#9cfce0]/40 bg-[#9cfce0]/10 text-[#9cfce0]">
              <FlaskConical className="h-4 w-4" />
            </span>
            <div>
              <p className="text-sm font-semibold">Timestamp_msi</p>
              <p className="text-xs text-[#89a79d]">MSI-H / MSS command surface</p>
            </div>
          </div>
          <div className="hidden items-center gap-2 md:flex">
            <Pill>TCGA CRC</Pill>
            <Pill>SVS: 60</Pill>
            <Pill>VM L4</Pill>
          </div>
        </header>

        <div className="grid flex-1 gap-6 py-6 xl:grid-cols-[minmax(0,1fr)_440px] xl:items-stretch">
          <section className="flex min-h-[620px] flex-col justify-between gap-8 rounded-[2rem] border border-white/10 bg-[#07110f]/70 p-5 shadow-2xl shadow-black/40 backdrop-blur-xl sm:p-8">
            <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_380px] lg:items-center">
              <div className="max-w-3xl">
                <div className="mb-6 flex flex-wrap items-center gap-2">
                  <span className="rounded-full border border-[#9cfce0]/30 bg-[#9cfce0]/10 px-3 py-1 text-xs font-semibold uppercase text-[#9cfce0]">
                    Bio-control room
                  </span>
                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-[#b7cfc7]">
                    local UI + VM pipeline
                  </span>
                </div>
                <h1 className="max-w-4xl text-5xl font-semibold leading-[0.94] text-[#f5fffb] sm:text-7xl lg:text-6xl 2xl:text-8xl">
                  MSI slide intelligence, live from the VM.
                </h1>
                <p className="mt-6 max-w-2xl text-base leading-8 text-[#b7cfc7] sm:text-lg">
                  Upload cohort files, check fold balance, inspect the remote
                  slide project, and launch Jupyter without leaving the browser.
                </p>
              </div>

              <BioField
                annotationRows={usableAnnotationRows}
                manifestRows={usableManifestRows}
                ready={readyChecks}
              />
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              <MetricTile
                label="Annotation rows"
                value={usableAnnotationRows.toLocaleString()}
                tone="teal"
              />
              <MetricTile
                label="Manifest rows"
                value={usableManifestRows.toLocaleString()}
                tone="blue"
              />
              <MetricTile
                label="VM state"
                value={vmBusy ? "Running" : readyChecks ? "Ready" : "Standby"}
                tone="coral"
              />
            </div>
          </section>

          <aside className="grid gap-4 xl:auto-rows-min">
            <FileDrop
              icon={<ClipboardList className="h-5 w-5" />}
              title="Annotations"
              description="Patient, slide, MSI label, and fold fields."
              fileText={fileLabel(annotations)}
              onFile={(file) => handleFile("annotations", file)}
            />

            <FileDrop
              icon={<Database className="h-5 w-5" />}
              title="GDC manifest"
              description="Diagnostic SVS manifest for the VM downloader."
              fileText={fileLabel(manifest)}
              onFile={(file) => handleFile("manifest", file)}
            />

            <Panel>
              <SectionTitle
                icon={<UploadCloud className="h-5 w-5" />}
                title="Send files"
                label="VM"
              />
              <div className="mt-4 grid gap-2">
                <ActionButton
                  busy={vmBusy === "uploadFile"}
                  disabled={!annotations || vmBusy === "uploadFile"}
                  icon={<ClipboardList className="h-4 w-4" />}
                  label="Upload annotations"
                  onClick={() => uploadToVm("annotations")}
                />
                <ActionButton
                  busy={vmBusy === "uploadFile"}
                  disabled={!manifest || vmBusy === "uploadFile"}
                  icon={<Database className="h-4 w-4" />}
                  label="Upload manifest"
                  onClick={() => uploadToVm("manifest")}
                />
              </div>
            </Panel>
          </aside>
        </div>
      </section>

      <section className="relative mx-auto grid w-full max-w-[1500px] gap-5 px-4 pb-10 sm:px-6 lg:px-8 xl:grid-cols-[420px_minmax(0,1fr)]">
        <aside className="space-y-5">
          <Panel>
            <SectionTitle
              icon={<Server className="h-5 w-5" />}
              title="VM run block"
              label="editable"
            />
            <textarea
              className="mt-4 min-h-64 w-full resize-y rounded-2xl border border-[#244640] bg-[#020605] p-4 font-mono text-xs leading-5 text-[#bfffe9] outline-none ring-0 transition focus:border-[#9cfce0]/60"
              value={activeCommand}
              onChange={(event) => setActiveCommand(event.target.value)}
              spellCheck={false}
            />
          </Panel>

          <Panel>
            <SectionTitle
              icon={<Play className="h-5 w-5" />}
              title="Fold balance"
              label="split"
            />
            <Distribution
              counts={foldCounts}
              emptyText="Fold counts appear after annotations load."
            />
          </Panel>
        </aside>

        <div className="space-y-5">
          <Panel>
            <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
              <SectionTitle
                icon={<Terminal className="h-5 w-5" />}
                title="VM control panel"
                label={vmBusy ? `running ${vmBusy}` : "ssh"}
              />
              <div className="grid gap-2 sm:grid-cols-2 xl:min-w-[540px]">
                <ActionButton
                  busy={vmBusy === "status"}
                  disabled={Boolean(vmBusy)}
                  icon={<RefreshCw className="h-4 w-4" />}
                  label="Check VM"
                  onClick={() => runVmAction("status")}
                />
                <ActionButton
                  busy={vmBusy === "listFiles"}
                  disabled={Boolean(vmBusy)}
                  icon={<FolderOpen className="h-4 w-4" />}
                  label="Browse project"
                  onClick={() => runVmAction("listFiles", { path: vmPath })}
                />
                <ActionButton
                  busy={vmBusy === "startDownloader"}
                  disabled={Boolean(vmBusy)}
                  icon={<HardDrive className="h-4 w-4" />}
                  label="Start downloader"
                  onClick={() => runVmAction("startDownloader")}
                />
                <ActionButton
                  busy={vmBusy === "startJupyter"}
                  disabled={Boolean(vmBusy)}
                  icon={<Play className="h-4 w-4" />}
                  label="Start Jupyter"
                  onClick={() => runVmAction("startJupyter")}
                />
                <ActionButton
                  busy={vmBusy === "startTunnel"}
                  disabled={Boolean(vmBusy)}
                  icon={<Server className="h-4 w-4" />}
                  label="Open tunnel"
                  onClick={() => runVmAction("startTunnel")}
                />
                <a
                  className="inline-flex min-h-11 items-center justify-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 text-sm font-semibold text-[#ecfff8] transition hover:border-[#9cfce0]/50 hover:bg-[#9cfce0]/10"
                  href="http://127.0.0.1:8888"
                  target="_blank"
                  rel="noreferrer"
                >
                  <Server className="h-4 w-4" />
                  Open Jupyter
                </a>
              </div>
            </div>

            <div className="mt-5 grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
              <div>
                <p className="mb-2 text-sm font-medium text-[#8fa9a0]">
                  SSH output
                </p>
                <pre className="max-h-80 min-h-52 overflow-auto rounded-3xl border border-[#244640] bg-[#020605] p-4 text-xs leading-5 text-[#c9ffe8] shadow-inner shadow-black/70">
                  {vmError || vmOutput}
                </pre>
              </div>

              <div>
                <p className="mb-2 text-sm font-medium text-[#8fa9a0]">
                  VM files
                </p>
                <div className="max-h-80 overflow-auto rounded-3xl border border-[#244640] bg-[#06100e]">
                  {vmFiles.length > 0 ? (
                    vmFiles.map((file) => (
                      <button
                        className="flex w-full items-center justify-between gap-3 border-b border-white/5 px-4 py-3 text-left text-sm transition last:border-b-0 hover:bg-[#9cfce0]/8"
                        key={`${file.type}-${file.name}`}
                        onClick={() => {
                          if (file.type === "d" && file.name !== ".") {
                            const nextPath = `${vmPath.replace(/\/$/, "")}/${file.name}`;
                            void runVmAction("listFiles", { path: nextPath });
                          }
                        }}
                        type="button"
                      >
                        <span className="min-w-0">
                          <span className="block truncate font-medium text-[#eefdf7]">
                            {file.name}
                          </span>
                          <span className="text-xs text-[#8fa9a0]">
                            {file.modified}
                          </span>
                        </span>
                        <span className="shrink-0 rounded-full border border-white/10 px-2 py-1 text-xs text-[#b7cfc7]">
                          {file.type === "d" ? "dir" : file.size}
                        </span>
                      </button>
                    ))
                  ) : (
                    <p className="p-4 text-sm leading-6 text-[#8fa9a0]">
                      Click Browse project after the VM check.
                    </p>
                  )}
                </div>
              </div>
            </div>
          </Panel>

          <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_340px]">
            <Panel>
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <SectionTitle
                  icon={<FileCheck2 className="h-5 w-5" />}
                  title="Cohort quality gate"
                  label={readyChecks ? "passed" : "waiting"}
                />
                <span
                  className={`inline-flex min-h-9 items-center justify-center gap-2 rounded-full border px-3 text-sm font-semibold ${
                    readyChecks
                      ? "border-[#9cfce0]/40 bg-[#9cfce0]/10 text-[#9cfce0]"
                      : "border-[#f5c46b]/40 bg-[#f5c46b]/10 text-[#f5c46b]"
                  }`}
                >
                  {readyChecks ? (
                    <FileCheck2 className="h-4 w-4" />
                  ) : (
                    <AlertTriangle className="h-4 w-4" />
                  )}
                  {readyChecks ? "Ready for VM" : "Needs files"}
                </span>
              </div>

              <div className="mt-5 grid gap-4 md:grid-cols-2">
                <ColumnCheck
                  title="Annotation fields"
                  columns={annotations?.columns ?? []}
                  missing={missingAnnotationFields}
                  detected={annotationMap}
                />
                <ColumnCheck
                  title="Manifest fields"
                  columns={manifest?.columns ?? []}
                  missing={missingManifestFields}
                  detected={manifestMap}
                />
              </div>
            </Panel>

            <Panel>
              <SectionTitle
                icon={<Activity className="h-5 w-5" />}
                title="Label mix"
                label="MSI"
              />
              <Distribution
                counts={labelCounts}
                emptyText="Upload annotations to see MSI-H/MSS counts."
              />
            </Panel>
          </section>

          <Panel>
            <SectionTitle
              icon={<FileText className="h-5 w-5" />}
              title="Workflow stages"
              label="pipeline"
            />
            <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              {stageRows.map((stage) => (
                <div
                  className="min-h-40 rounded-3xl border border-white/10 bg-white/[0.04] p-4"
                  key={stage.name}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h3 className="font-semibold text-[#f5fffb]">
                        {stage.name}
                      </h3>
                      <p className="mt-1 text-xs font-semibold uppercase text-[#72f2cc]">
                        {stage.owner}
                      </p>
                    </div>
                    <span className="rounded-full border border-white/10 px-2 py-1 text-xs text-[#b7cfc7]">
                      {stage.state}
                    </span>
                  </div>
                  <p className="mt-4 text-sm leading-6 text-[#a7c2b9]">
                    {stage.detail}
                  </p>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      </section>
    </main>
  );
}

function Panel({ children }: { children: React.ReactNode }) {
  return (
    <section className="rounded-[1.6rem] border border-white/10 bg-[#07110f]/75 p-4 shadow-xl shadow-black/25 backdrop-blur-xl sm:p-5">
      {children}
    </section>
  );
}

function SectionTitle({
  icon,
  title,
  label,
}: {
  icon: React.ReactNode;
  title: string;
  label: string;
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div className="flex items-center gap-3">
        <span className="flex h-10 w-10 items-center justify-center rounded-full border border-[#9cfce0]/25 bg-[#9cfce0]/10 text-[#9cfce0]">
          {icon}
        </span>
        <h2 className="text-xl font-semibold text-[#f5fffb]">{title}</h2>
      </div>
      <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-semibold uppercase text-[#8fa9a0]">
        {label}
      </span>
    </div>
  );
}

function Pill({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-xs font-semibold text-[#b7cfc7]">
      {children}
    </span>
  );
}

function BioField({
  annotationRows,
  manifestRows,
  ready,
}: {
  annotationRows: number;
  manifestRows: number;
  ready: boolean;
}) {
  return (
    <div className="relative mx-auto aspect-square w-full max-w-[380px] overflow-hidden rounded-[2rem] border border-white/10 bg-[#071513] shadow-2xl shadow-black/40">
      <div className="absolute inset-0 bg-[linear-gradient(120deg,rgba(156,252,224,0.2),transparent_38%),linear-gradient(300deg,rgba(133,165,255,0.18),transparent_36%)]" />
      <div className="absolute inset-8 rounded-[1.6rem] border border-[#9cfce0]/20 bg-[#020605]/55" />
      <div className="absolute left-10 right-10 top-16 h-px bg-[#9cfce0]/30" />
      <div className="absolute bottom-16 left-10 right-10 h-px bg-[#9cfce0]/30" />
      <div className="absolute left-16 top-10 bottom-10 w-px bg-[#9cfce0]/30" />
      <div className="absolute right-16 top-10 bottom-10 w-px bg-[#9cfce0]/30" />
      <div className="absolute inset-0">
        {Array.from({ length: 15 }).map((_, index) => (
          <span
            className="absolute h-2 w-8 rounded-full bg-[#9cfce0]/60 shadow-[0_0_22px_rgba(156,252,224,0.42)]"
            key={index}
            style={{
              left: `${18 + (index % 5) * 15}%`,
              top: `${18 + Math.floor(index / 5) * 22}%`,
              transform: `rotate(${index % 2 === 0 ? -24 : 24}deg)`,
              opacity: 0.35 + (index % 4) * 0.12,
            }}
          />
        ))}
      </div>
      <div className="absolute left-8 top-8 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-semibold text-[#d9fff3]">
        WSI / MSI
      </div>
      <div className="absolute bottom-8 left-8 right-8 grid grid-cols-3 gap-2">
        <BioStat label="ANN" value={annotationRows} />
        <BioStat label="GDC" value={manifestRows} />
        <BioStat label="VM" value={ready ? "OK" : "IDLE"} />
      </div>
    </div>
  );
}

function BioStat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-[#020605]/70 p-3">
      <p className="text-[10px] font-semibold text-[#72f2cc]">{label}</p>
      <p className="mt-1 truncate text-lg font-semibold text-[#f5fffb]">
        {value}
      </p>
    </div>
  );
}

function MetricTile({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: "teal" | "blue" | "coral";
}) {
  const color =
    tone === "teal"
      ? "text-[#9cfce0]"
      : tone === "blue"
        ? "text-[#9fb6ff]"
        : "text-[#ff9f8d]";

  return (
    <div className="min-h-28 rounded-[1.4rem] border border-white/10 bg-white/[0.04] p-4">
      <p className="text-sm text-[#8fa9a0]">{label}</p>
      <p className={`mt-3 truncate text-3xl font-semibold ${color}`}>{value}</p>
    </div>
  );
}

function FileDrop({
  icon,
  title,
  description,
  fileText,
  onFile,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
  fileText: string;
  onFile: (file?: File) => void;
}) {
  return (
    <section className="rounded-[1.6rem] border border-white/10 bg-[#07110f]/75 p-4 shadow-xl shadow-black/25 backdrop-blur-xl sm:p-5">
      <div className="flex items-start gap-3">
        <span className="flex h-10 w-10 items-center justify-center rounded-full border border-[#9cfce0]/25 bg-[#9cfce0]/10 text-[#9cfce0]">
          {icon}
        </span>
        <div>
          <h2 className="text-base font-semibold text-[#f5fffb]">{title}</h2>
          <p className="mt-1 text-sm leading-6 text-[#8fa9a0]">{description}</p>
        </div>
      </div>

      <label className="mt-4 flex min-h-12 cursor-pointer items-center justify-between gap-3 rounded-full border border-dashed border-[#45655d] bg-white/[0.04] px-4 text-sm transition hover:border-[#9cfce0]/60 hover:bg-[#9cfce0]/10">
        <span className="flex min-w-0 items-center gap-2 text-[#b7cfc7]">
          <Upload className="h-4 w-4 shrink-0" />
          <span className="truncate">{fileText}</span>
        </span>
        <span className="shrink-0 rounded-full bg-[#dffff4] px-3 py-1 font-semibold text-[#04110f]">
          Choose
        </span>
        <input
          accept=".csv,.tsv,.txt"
          className="sr-only"
          type="file"
          onChange={(event) => onFile(event.target.files?.[0])}
        />
      </label>
    </section>
  );
}

function ActionButton({
  busy,
  disabled,
  icon,
  label,
  onClick,
}: {
  busy?: boolean;
  disabled?: boolean;
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      className="inline-flex min-h-11 items-center justify-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 text-sm font-semibold text-[#ecfff8] transition hover:border-[#9cfce0]/50 hover:bg-[#9cfce0]/10 disabled:cursor-not-allowed disabled:opacity-45"
      disabled={disabled}
      onClick={onClick}
      type="button"
    >
      {icon}
      {busy ? "Running..." : label}
    </button>
  );
}

function ColumnCheck({
  title,
  columns,
  missing,
  detected,
}: {
  title: string;
  columns: string[];
  missing: string[];
  detected: Record<string, string | undefined>;
}) {
  return (
    <div className="rounded-3xl border border-white/10 bg-white/[0.035] p-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-semibold text-[#f5fffb]">{title}</h3>
        <span className="text-sm text-[#8fa9a0]">{columns.length} columns</span>
      </div>
      <div className="mt-4 grid gap-2">
        {Object.entries(detected).map(([field, column]) => (
          <div
            className="flex min-h-10 items-center justify-between gap-3 rounded-2xl border border-white/5 bg-[#020605]/45 px-3 text-sm"
            key={field}
          >
            <span className="font-medium capitalize text-[#b7cfc7]">{field}</span>
            <span className={column ? "text-[#9cfce0]" : "text-[#ff9f8d]"}>
              {column ?? "Missing"}
            </span>
          </div>
        ))}
      </div>
      {missing.length > 0 ? (
        <p className="mt-3 text-sm leading-6 text-[#f5c46b]">
          Missing required mapping: {missing.join(", ")}.
        </p>
      ) : (
        <p className="mt-3 text-sm leading-6 text-[#9cfce0]">
          Required mappings are present.
        </p>
      )}
    </div>
  );
}

function Distribution({
  counts,
  emptyText,
}: {
  counts: Record<string, number>;
  emptyText: string;
}) {
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  const total = entries.reduce((sum, [, value]) => sum + value, 0);

  if (entries.length === 0) {
    return <p className="mt-4 text-sm leading-6 text-[#8fa9a0]">{emptyText}</p>;
  }

  return (
    <div className="mt-4 space-y-4">
      {entries.map(([label, value], index) => {
        const percent = total > 0 ? Math.round((value / total) * 100) : 0;
        const bar =
          index % 3 === 0
            ? "bg-[#9cfce0]"
            : index % 3 === 1
              ? "bg-[#9fb6ff]"
              : "bg-[#ff9f8d]";

        return (
          <div key={label}>
            <div className="mb-2 flex items-center justify-between gap-3 text-sm">
              <span className="font-semibold text-[#eefdf7]">{label}</span>
              <span className="text-[#8fa9a0]">
                {value.toLocaleString()} ({percent}%)
              </span>
            </div>
            <div className="h-2 rounded-full bg-white/10">
              <div
                className={`h-2 rounded-full ${bar}`}
                style={{ width: `${Math.max(percent, 2)}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
