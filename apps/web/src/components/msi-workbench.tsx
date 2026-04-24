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
    state: "Ready to validate",
  },
  {
    name: "Slide acquisition",
    owner: "VM storage",
    detail: "Download SVS files to the remote slide folder, not Windows",
    state: "Needs manifest",
  },
  {
    name: "Feature extraction",
    owner: "pathology310",
    detail: "Run the notebook against the remote kernel with CUDA checks first",
    state: "Notebook path",
  },
  {
    name: "Slideflow training",
    owner: "MIL workflow",
    detail: "Use patient-level folds to avoid leakage",
    state: "After slides",
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
    <main className="min-h-screen bg-[#f7f8f5] text-[#171b18]">
      <section className="border-b border-[#d7ded5] bg-[#fbfcf7]">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-5 py-6 sm:px-8 lg:px-10">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <div className="mb-3 flex flex-wrap items-center gap-2 text-sm font-medium text-[#526258]">
                <span className="inline-flex items-center gap-2 rounded border border-[#cfd9d1] bg-white px-3 py-1">
                  <FlaskConical className="h-4 w-4 text-[#00856f]" />
                  Approach 1
                </span>
                <span>TCGA CRC MSI research workstation</span>
              </div>
              <h1 className="text-3xl font-semibold leading-tight sm:text-5xl">
                MSI-H vs MSS slide pipeline control room
              </h1>
              <p className="mt-4 max-w-2xl text-base leading-7 text-[#526258]">
                Validate annotation and GDC manifest files locally, check fold
                balance before training, and keep the heavy SVS download path on
                the pathology VM.
              </p>
            </div>

            <div className="grid min-w-full grid-cols-2 gap-3 sm:min-w-[420px]">
              <MetricTile
                label="Annotation rows"
                value={usableAnnotationRows.toLocaleString()}
                tone="teal"
              />
              <MetricTile
                label="Manifest rows"
                value={usableManifestRows.toLocaleString()}
                tone="amber"
              />
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto grid w-full max-w-7xl gap-5 px-5 py-6 sm:px-8 lg:grid-cols-[380px_minmax(0,1fr)] lg:px-10">
        <aside className="space-y-5">
          <FileDrop
            icon={<ClipboardList className="h-5 w-5" />}
            title="Annotations"
            description="Upload the MSI label CSV with patient, slide, label, and fold fields."
            fileText={fileLabel(annotations)}
            onFile={(file) => handleFile("annotations", file)}
          />

          <FileDrop
            icon={<Database className="h-5 w-5" />}
            title="GDC manifest"
            description="Upload the diagnostic SVS manifest TSV or CSV used by the VM downloader."
            fileText={fileLabel(manifest)}
            onFile={(file) => handleFile("manifest", file)}
          />

          <section className="rounded-lg border border-[#d7ded5] bg-white p-4">
            <div className="mb-4 flex items-center gap-2">
              <Server className="h-5 w-5 text-[#3751a3]" />
              <h2 className="text-base font-semibold">VM run block</h2>
            </div>
            <textarea
              className="min-h-56 w-full resize-y rounded border border-[#cfd9d1] bg-[#101511] p-3 font-mono text-xs leading-5 text-[#d7f5dc] outline-none focus:border-[#00856f]"
              value={activeCommand}
              onChange={(event) => setActiveCommand(event.target.value)}
              spellCheck={false}
            />
          </section>

          <section className="rounded-lg border border-[#d7ded5] bg-white p-4">
            <div className="mb-4 flex items-center gap-2">
              <UploadCloud className="h-5 w-5 text-[#00856f]" />
              <h2 className="text-base font-semibold">Send files to VM</h2>
            </div>
            <div className="grid gap-2">
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
          </section>
        </aside>

        <div className="space-y-5">
          <section className="rounded-lg border border-[#d7ded5] bg-white p-5">
            <div className="mb-5 flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
              <div>
                <div className="mb-2 flex items-center gap-2">
                  <Terminal className="h-5 w-5 text-[#3751a3]" />
                  <h2 className="text-xl font-semibold">VM control panel</h2>
                </div>
                <p className="text-sm leading-6 text-[#526258]">
                  Buttons run fixed SSH actions through the local Next server
                  using your `evolet_rsa` key. The key never enters browser
                  JavaScript.
                </p>
              </div>
              <div className="grid gap-2 sm:grid-cols-2 xl:min-w-[520px]">
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
                  className="inline-flex min-h-10 items-center justify-center gap-2 rounded border border-[#cfd9d1] bg-[#fbfcf7] px-3 text-sm font-medium text-[#171b18] transition hover:border-[#00856f] hover:bg-[#f0f8f3]"
                  href="http://127.0.0.1:8888"
                  target="_blank"
                  rel="noreferrer"
                >
                  <Server className="h-4 w-4" />
                  Open Jupyter
                </a>
              </div>
            </div>

            <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
              <div>
                <div className="mb-2 flex items-center justify-between gap-3">
                  <p className="text-sm font-medium text-[#526258]">
                    SSH output
                  </p>
                  {vmBusy ? (
                    <span className="text-sm text-[#87610b]">
                      Running {vmBusy}...
                    </span>
                  ) : null}
                </div>
                <pre className="max-h-80 min-h-44 overflow-auto rounded border border-[#cfd9d1] bg-[#101511] p-3 text-xs leading-5 text-[#d7f5dc]">
                  {vmError || vmOutput}
                </pre>
              </div>

              <div>
                <p className="mb-2 text-sm font-medium text-[#526258]">
                  VM files
                </p>
                <div className="max-h-80 overflow-auto rounded border border-[#d7ded5]">
                  {vmFiles.length > 0 ? (
                    vmFiles.map((file) => (
                      <button
                        className="flex w-full items-center justify-between gap-3 border-b border-[#eef2ec] bg-[#fbfcf7] px-3 py-2 text-left text-sm last:border-b-0 hover:bg-[#f0f8f3]"
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
                          <span className="block truncate font-medium">
                            {file.name}
                          </span>
                          <span className="text-xs text-[#708077]">
                            {file.modified}
                          </span>
                        </span>
                        <span className="shrink-0 text-xs text-[#526258]">
                          {file.type === "d" ? "dir" : file.size}
                        </span>
                      </button>
                    ))
                  ) : (
                    <p className="p-3 text-sm leading-6 text-[#526258]">
                      Click Browse project after the VM check.
                    </p>
                  )}
                </div>
              </div>
            </div>
          </section>

          <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_330px]">
            <div className="rounded-lg border border-[#d7ded5] bg-white p-5">
              <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h2 className="text-xl font-semibold">Cohort quality gate</h2>
                  <p className="mt-1 text-sm leading-6 text-[#526258]">
                    The app only reports what exists in the uploaded files.
                    Missing fields stay visible until fixed.
                  </p>
                </div>
                <span
                  className={`inline-flex items-center gap-2 rounded border px-3 py-1 text-sm font-medium ${
                    readyChecks
                      ? "border-[#a4cdbb] bg-[#e9f8f1] text-[#006c5a]"
                      : "border-[#e5c68c] bg-[#fff7e2] text-[#87610b]"
                  }`}
                >
                  {readyChecks ? (
                    <FileCheck2 className="h-4 w-4" />
                  ) : (
                    <AlertTriangle className="h-4 w-4" />
                  )}
                  {readyChecks ? "Ready for VM run" : "Needs file checks"}
                </span>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
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
            </div>

            <div className="rounded-lg border border-[#d7ded5] bg-white p-5">
              <div className="mb-5 flex items-center gap-2">
                <Activity className="h-5 w-5 text-[#a1443c]" />
                <h2 className="text-xl font-semibold">Label mix</h2>
              </div>
              <Distribution
                counts={labelCounts}
                emptyText="Upload annotations to see MSI-H/MSS counts."
              />
            </div>
          </section>

          <section className="grid gap-5 xl:grid-cols-[330px_minmax(0,1fr)]">
            <div className="rounded-lg border border-[#d7ded5] bg-white p-5">
              <div className="mb-5 flex items-center gap-2">
                <Play className="h-5 w-5 text-[#00856f]" />
                <h2 className="text-xl font-semibold">Fold balance</h2>
              </div>
              <Distribution
                counts={foldCounts}
                emptyText="Fold counts appear after an annotation file is loaded."
              />
            </div>

            <div className="rounded-lg border border-[#d7ded5] bg-white p-5">
              <div className="mb-5 flex items-center gap-2">
                <FileText className="h-5 w-5 text-[#3751a3]" />
                <h2 className="text-xl font-semibold">Workflow stages</h2>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                {stageRows.map((stage) => (
                  <div
                    className="rounded border border-[#d7ded5] bg-[#fbfcf7] p-4"
                    key={stage.name}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h3 className="font-semibold">{stage.name}</h3>
                        <p className="mt-1 text-xs font-medium uppercase text-[#708077]">
                          {stage.owner}
                        </p>
                      </div>
                      <span className="rounded border border-[#cfd9d1] bg-white px-2 py-1 text-xs text-[#526258]">
                        {stage.state}
                      </span>
                    </div>
                    <p className="mt-3 text-sm leading-6 text-[#526258]">
                      {stage.detail}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </section>
        </div>
      </section>
    </main>
  );
}

function MetricTile({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: "teal" | "amber";
}) {
  const color = tone === "teal" ? "text-[#00856f]" : "text-[#a66a00]";

  return (
    <div className="rounded-lg border border-[#d7ded5] bg-white p-4">
      <p className="text-sm text-[#526258]">{label}</p>
      <p className={`mt-2 text-3xl font-semibold ${color}`}>{value}</p>
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
    <section className="rounded-lg border border-[#d7ded5] bg-white p-4">
      <div className="flex items-start gap-3">
        <span className="rounded border border-[#cfd9d1] bg-[#f7f8f5] p-2 text-[#00856f]">
          {icon}
        </span>
        <div>
          <h2 className="text-base font-semibold">{title}</h2>
          <p className="mt-1 text-sm leading-6 text-[#526258]">
            {description}
          </p>
        </div>
      </div>

      <label className="mt-4 flex cursor-pointer items-center justify-between gap-3 rounded border border-dashed border-[#b8c6bb] bg-[#fbfcf7] px-3 py-3 text-sm transition hover:border-[#00856f] hover:bg-[#f0f8f3]">
        <span className="flex min-w-0 items-center gap-2 text-[#526258]">
          <Upload className="h-4 w-4 shrink-0" />
          <span className="truncate">{fileText}</span>
        </span>
        <span className="shrink-0 rounded bg-[#171b18] px-3 py-1 font-medium text-white">
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
      className="inline-flex min-h-10 items-center justify-center gap-2 rounded border border-[#cfd9d1] bg-[#fbfcf7] px-3 text-sm font-medium text-[#171b18] transition hover:border-[#00856f] hover:bg-[#f0f8f3] disabled:cursor-not-allowed disabled:opacity-50"
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
    <div className="rounded border border-[#d7ded5] bg-[#fbfcf7] p-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-semibold">{title}</h3>
        <span className="text-sm text-[#526258]">{columns.length} columns</span>
      </div>
      <div className="mt-4 grid gap-2">
        {Object.entries(detected).map(([field, column]) => (
          <div
            className="flex items-center justify-between gap-3 rounded bg-white px-3 py-2 text-sm"
            key={field}
          >
            <span className="font-medium capitalize">{field}</span>
            <span className={column ? "text-[#006c5a]" : "text-[#a1443c]"}>
              {column ?? "Missing"}
            </span>
          </div>
        ))}
      </div>
      {missing.length > 0 ? (
        <p className="mt-3 text-sm leading-6 text-[#87610b]">
          Missing required mapping: {missing.join(", ")}.
        </p>
      ) : (
        <p className="mt-3 text-sm leading-6 text-[#006c5a]">
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
    return <p className="text-sm leading-6 text-[#526258]">{emptyText}</p>;
  }

  return (
    <div className="space-y-3">
      {entries.map(([label, value], index) => {
        const percent = total > 0 ? Math.round((value / total) * 100) : 0;
        const bar =
          index % 3 === 0
            ? "bg-[#00856f]"
            : index % 3 === 1
              ? "bg-[#a66a00]"
              : "bg-[#3751a3]";

        return (
          <div key={label}>
            <div className="mb-1 flex items-center justify-between gap-3 text-sm">
              <span className="font-medium">{label}</span>
              <span className="text-[#526258]">
                {value.toLocaleString()} ({percent}%)
              </span>
            </div>
            <div className="h-2 rounded bg-[#e7ece6]">
              <div
                className={`h-2 rounded ${bar}`}
                style={{ width: `${Math.max(percent, 2)}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
