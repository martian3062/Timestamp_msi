"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  ClipboardList,
  Database,
  Dice5,
  FileCheck2,
  FileText,
  FlaskConical,
  FolderOpen,
  HardDrive,
  Moon,
  Play,
  RefreshCw,
  Server,
  Shield,
  Sigma,
  Sun,
  Terminal,
  TrendingUp,
  Upload,
  UploadCloud,
} from "lucide-react";
import { WinterScene } from "@/components/winter-scene";
import type { DistributionDatum } from "@/components/recharts-distribution";

const RechartsDistribution = dynamic(
  () =>
    import("@/components/recharts-distribution").then(
      (module) => module.RechartsDistribution,
    ),
  {
    ssr: false,
    loading: () => (
      <div className="mt-4 h-52 rounded-3xl border border-white/60 bg-white/35" />
    ),
  },
);

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

type BestExperiment = {
  primary_metric: string;
  metric_direction: "max" | "min";
  completed_trials: number;
  best: {
    trial_id: string;
    metric: string;
    value: number;
    metrics: Record<string, unknown>;
  } | null;
};

type IntegrationStatus = {
  name: string;
  env_var: string;
  configured: boolean;
  use: string;
};

type MCTrial = {
  trial_id: string;
  feature_extractor: string;
  mil_model: string;
  learning_rate: number;
  dropout: number;
  weight_decay: number;
  epochs: number;
  seed: number;
};

type MCPlan = {
  trial_count: number;
  random_seed: number;
  rank_formula: string;
  trials: MCTrial[];
};

type MCDropoutResult = {
  ok: boolean;
  trial_id: string;
  forward_passes: number;
  slide_count: number;
  mean_uncertainty: number;
  high_confidence_pct: number;
  medium_confidence_pct: number;
  low_confidence_pct: number;
};

type BootstrapCI = {
  ok: boolean;
  trial_id: string;
  n_bootstrap: number;
  ci_level: number;
  metrics: {
    metric: string;
    point_estimate: number;
    ci_lower: number;
    ci_upper: number;
    ci_level: number;
    std_error: number;
  }[];
};

type StableBestResult = {
  ok: boolean;
  rank_formula: string;
  total_evaluated: number;
  best: {
    trial_id: string;
    mean_auroc: number;
    sd_auroc: number;
    mean_auprc: number;
    sd_auprc: number;
    stability_score: number;
    folds_completed: number;
    feature_extractor: string;
    mil_model: string;
  } | null;
  candidates: {
    trial_id: string;
    stability_score: number;
    mean_auroc: number;
    sd_auroc: number;
  }[];
};

const requiredAnnotationFields = ["patient", "slide", "label", "fold"];
const requiredManifestFields = ["id", "filename"];
const automationApiBase =
  process.env.NEXT_PUBLIC_MSI_API_URL ?? "http://127.0.0.1:8001";
const chartPalette = ["#168f8b", "#4666d9", "#d95d48", "#7b61ff", "#d99a21"];

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
  const [bestExperiment, setBestExperiment] = useState<BestExperiment>();
  const [integrations, setIntegrations] = useState<IntegrationStatus[]>([]);
  const [automationError, setAutomationError] = useState("");
  const [activeCommand, setActiveCommand] = useState(commandBlock);
  const [vmBusy, setVmBusy] = useState<string>();
  const [vmOutput, setVmOutput] = useState("Run a VM check to see live status.");
  const [vmError, setVmError] = useState("");
  const [vmPath, setVmPath] = useState(
    "/home/pardeep/pathology310_projects/single_slide_morphology/project_1_slideflow_msi_tcga_crc",
  );
  const [vmFiles, setVmFiles] = useState<VmFileRow[]>([]);

  /* Theme state — dark by default */
  const [theme, setTheme] = useState<"dark-theme" | "snow-theme">("dark-theme");
  const isDark = theme === "dark-theme";

  /* Monte Carlo state */
  const [mcPlan, setMcPlan] = useState<MCPlan>();
  const [mcBusy, setMcBusy] = useState<string>();
  const [mcDropout, setMcDropout] = useState<MCDropoutResult>();
  const [mcBootstrapCI, setMcBootstrapCI] = useState<BootstrapCI>();
  const [mcStableBest, setMcStableBest] = useState<StableBestResult>();
  const [mcError, setMcError] = useState("");

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

  useEffect(() => {
    let cancelled = false;

    async function refreshAutomation() {
      try {
        const [bestResponse, integrationsResponse] = await Promise.all([
          fetch(
            `${automationApiBase}/experiments/best?primary_metric=mean_auroc&metric_direction=max`,
          ),
          fetch(`${automationApiBase}/integrations/status`),
        ]);

        if (!bestResponse.ok || !integrationsResponse.ok) {
          throw new Error("Automation API is not ready.");
        }

        const bestData = (await bestResponse.json()) as BestExperiment;
        const integrationData = (await integrationsResponse.json()) as {
          integrations: IntegrationStatus[];
        };

        if (!cancelled) {
          setBestExperiment(bestData);
          setIntegrations(integrationData.integrations);
          setAutomationError("");
        }
      } catch (error) {
        if (!cancelled) {
          setAutomationError(
            error instanceof Error
              ? error.message
              : "Automation API is not reachable.",
          );
        }
      }
    }

    void refreshAutomation();

    return () => {
      cancelled = true;
    };
  }, []);

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

  /* Monte Carlo actions */
  async function generateMCPlan() {
    setMcBusy("plan");
    setMcError("");
    try {
      const response = await fetch(`${automationApiBase}/experiments/monte-carlo-plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ samples: 8, random_seed: 310, folds: [1], epoch_choices: [5, 10, 20] }),
      });
      if (!response.ok) throw new Error("Failed to generate MC plan");
      const data = (await response.json()) as MCPlan;
      setMcPlan(data);
    } catch (error) {
      setMcError(error instanceof Error ? error.message : "MC plan failed");
    } finally {
      setMcBusy(undefined);
    }
  }

  async function fetchMCDropout(trialId: string) {
    setMcBusy("dropout");
    setMcError("");
    try {
      const response = await fetch(`${automationApiBase}/experiments/uncertainty/${trialId}`);
      if (!response.ok) throw new Error("Failed to fetch MC dropout");
      const data = (await response.json()) as MCDropoutResult;
      setMcDropout(data);
    } catch (error) {
      setMcError(error instanceof Error ? error.message : "MC dropout fetch failed");
    } finally {
      setMcBusy(undefined);
    }
  }

  async function fetchBootstrapCI(trialId: string) {
    setMcBusy("bootstrap");
    setMcError("");
    try {
      const response = await fetch(`${automationApiBase}/experiments/bootstrap-ci/${trialId}`);
      if (!response.ok) throw new Error("Failed to fetch bootstrap CI");
      const data = (await response.json()) as BootstrapCI;
      setMcBootstrapCI(data);
    } catch (error) {
      setMcError(error instanceof Error ? error.message : "Bootstrap CI fetch failed");
    } finally {
      setMcBusy(undefined);
    }
  }

  async function fetchStableBest() {
    setMcBusy("stableBest");
    setMcError("");
    try {
      const response = await fetch(`${automationApiBase}/experiments/best-stable?rank_formula=mean_auroc%20-%200.5%20*%20sd_auroc&min_completed_folds=1`);
      if (!response.ok) throw new Error("Failed to fetch stable best");
      const data = (await response.json()) as StableBestResult;
      setMcStableBest(data);
    } catch (error) {
      setMcError(error instanceof Error ? error.message : "Stable best failed");
    } finally {
      setMcBusy(undefined);
    }
  }

  async function bootstrapMCRunners() {
    setMcBusy("bootstrap-runners");
    setMcError("");
    try {
      const response = await fetch(`${automationApiBase}/experiments/mc-bootstrap`, { method: "POST" });
      if (!response.ok) throw new Error("Failed to bootstrap MC runners");
    } catch (error) {
      setMcError(error instanceof Error ? error.message : "Bootstrap runners failed");
    } finally {
      setMcBusy(undefined);
    }
  }

  return (
    <main className={`${theme} min-h-screen overflow-hidden`} style={{ background: "var(--background)", color: "var(--foreground)" }}>
      <video
        aria-hidden="true"
        autoPlay
        className="pointer-events-none fixed inset-0 z-0 h-full w-full object-cover"
        loop
        muted
        playsInline
        src="/assets/snow-in-jinan.webm"
        style={{
          filter: isDark ? "saturate(0.55) brightness(0.6) contrast(1.1)" : "saturate(0.55) brightness(1.2) contrast(0.82)",
          opacity: isDark ? 0.18 : 0.28,
        }}
      />
      <div className="snow-video-veil" />
      <div className="mouse-aura" />
      {isDark ? (
        <div className="pointer-events-none fixed inset-0 bg-[linear-gradient(115deg,rgba(156,252,224,0.04),transparent_42%),linear-gradient(245deg,rgba(70,102,217,0.06),transparent_36%),radial-gradient(circle_at_50%_-10%,rgba(156,252,224,0.06),transparent_34%)]" />
      ) : (
        <div className="pointer-events-none fixed inset-0 bg-[linear-gradient(115deg,rgba(255,255,255,0.82),transparent_42%),linear-gradient(245deg,rgba(176,223,255,0.34),transparent_36%),radial-gradient(circle_at_50%_-10%,rgba(255,255,255,0.78),transparent_34%)]" />
      )}
      <div className="pointer-events-none fixed inset-0 bg-[linear-gradient(rgba(30,75,82,0.055)_1px,transparent_1px),linear-gradient(90deg,rgba(30,75,82,0.055)_1px,transparent_1px)] bg-[size:72px_72px] opacity-50" />
      <section className="relative z-10 mx-auto flex min-h-[92vh] w-full max-w-[1500px] flex-col px-4 pb-8 pt-4 sm:px-6 lg:px-8">
        <header className="flex min-h-14 items-center justify-between border-b border-white/10">
          <div className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-full border border-[#9cfce0]/40 bg-[#9cfce0]/10 text-[#9cfce0]">
              <FlaskConical className="h-4 w-4" />
            </span>
            <div>
              <p className="text-sm font-semibold" style={{ color: "var(--heading)" }}>Timestamp_msi</p>
              <p className="text-xs" style={{ color: "var(--muted)" }}>MSI-H / MSS command surface</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="hidden items-center gap-2 md:flex">
              <Pill isDark={isDark}>TCGA CRC</Pill>
              <Pill isDark={isDark}>SVS: batch 10</Pill>
              <Pill isDark={isDark}>VM L4</Pill>
            </div>
            <button
              className="flex h-9 w-9 items-center justify-center rounded-full border transition-colors"
              style={{
                borderColor: isDark ? "rgba(156,252,224,0.3)" : "rgba(255,255,255,0.7)",
                background: isDark ? "rgba(156,252,224,0.1)" : "rgba(255,255,255,0.5)",
                color: isDark ? "#9cfce0" : "#143536",
              }}
              onClick={() => setTheme(isDark ? "snow-theme" : "dark-theme")}
              type="button"
              title={isDark ? "Switch to light mode" : "Switch to dark mode"}
            >
              {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </button>
          </div>
        </header>

        <div className="grid flex-1 gap-6 py-6 xl:grid-cols-[minmax(0,1fr)_440px] xl:items-stretch">
          <section className="reactive-surface flex min-h-[620px] flex-col justify-between gap-8 rounded-[2rem] p-5 shadow-2xl backdrop-blur-2xl sm:p-8" style={{ background: "var(--panel-bg)", borderColor: "var(--panel-border)", boxShadow: "var(--panel-shadow)" }}>
            <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_380px] lg:items-center">
              <div className="max-w-3xl">
                <div className="mb-6 flex flex-wrap items-center gap-2">
                  <span className="rounded-full px-3 py-1 text-xs font-semibold uppercase" style={{ border: "1px solid var(--accent-border)", background: "var(--accent-dim)", color: "var(--tag-text)" }}>
                    Bio-control room
                  </span>
                  <span className="rounded-full border px-3 py-1 text-xs" style={{ borderColor: "var(--border)", background: "var(--btn-bg)", color: "var(--muted)" }}>
                    local UI + VM pipeline
                  </span>
                </div>
                <h1 className="max-w-4xl text-5xl font-semibold leading-[0.94] sm:text-7xl lg:text-6xl 2xl:text-8xl" style={{ color: "var(--heading)" }}>
                  MSI slide intelligence, live from the VM.
                </h1>
                <p className="mt-6 max-w-2xl text-base leading-8 sm:text-lg" style={{ color: "var(--body)" }}>
                  Upload cohort files, check fold balance, inspect the remote
                  slide project, and launch Jupyter without leaving the browser.
                </p>
              </div>

              <div className="interactive-igloo-wrap">
                <WinterScene dx={0} dy={0} />
              </div>
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

      <section className="relative z-10 mx-auto grid w-full max-w-[1500px] gap-5 px-4 pb-10 sm:px-6 lg:px-8 xl:grid-cols-[420px_minmax(0,1fr)]">
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

          <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_420px]">
            <Panel>
              <SectionTitle
                icon={<Activity className="h-5 w-5" />}
                title="Experiment result"
                label={
                  bestExperiment?.completed_trials
                    ? `${bestExperiment.completed_trials} done`
                    : "pending"
                }
              />
              <ExperimentResult
                bestExperiment={bestExperiment}
                error={automationError}
              />
            </Panel>

            <Panel>
              <SectionTitle
                icon={<Database className="h-5 w-5" />}
                title="Tech surface"
                label="stack"
              />
              <TechSurface integrations={integrations} />
            </Panel>
          </section>

          {/* Monte Carlo Methods Panel */}
          <Panel>
            <SectionTitle
              icon={<Dice5 className="h-5 w-5" />}
              title="Monte Carlo methods"
              label={mcPlan ? `${mcPlan.trial_count} trials` : "hft-methods"}
            />

            {mcError ? (
              <p className="mt-4 rounded-2xl border border-[#d95d48]/30 bg-[#d95d48]/10 p-3 text-sm leading-6 text-[#8a2c21]">
                {mcError}
              </p>
            ) : null}

            <div className="mt-5 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
              <ActionButton
                busy={mcBusy === "plan"}
                disabled={Boolean(mcBusy)}
                icon={<Dice5 className="h-4 w-4" />}
                label="Generate MC plan"
                onClick={() => generateMCPlan()}
              />
              <ActionButton
                busy={mcBusy === "bootstrap-runners"}
                disabled={Boolean(mcBusy)}
                icon={<Upload className="h-4 w-4" />}
                label="Bootstrap runners"
                onClick={() => bootstrapMCRunners()}
              />
              <ActionButton
                busy={mcBusy === "stableBest"}
                disabled={Boolean(mcBusy)}
                icon={<TrendingUp className="h-4 w-4" />}
                label="Stable best"
                onClick={() => fetchStableBest()}
              />
              <ActionButton
                busy={mcBusy === "dropout" || mcBusy === "bootstrap"}
                disabled={Boolean(mcBusy) || !bestExperiment?.best}
                icon={<Sigma className="h-4 w-4" />}
                label="Uncertainty check"
                onClick={() => {
                  const tid = bestExperiment?.best?.trial_id;
                  if (tid) {
                    void fetchMCDropout(tid);
                    void fetchBootstrapCI(tid);
                  }
                }}
              />
            </div>

            {/* MC Random search plan */}
            {mcPlan ? (
              <div className="mt-5">
                <div className="mb-3 flex items-center gap-2">
                  <BarChart3 className="h-4 w-4 text-[#9cfce0]" />
                  <p className="text-sm font-semibold text-[#102b2b]">
                    Random search plan
                    <span className="ml-2 text-xs font-normal text-[#8fa9a0]">
                      seed {mcPlan.random_seed} · {mcPlan.rank_formula}
                    </span>
                  </p>
                </div>
                <div className="max-h-64 overflow-auto rounded-2xl border border-white/60 bg-white/40">
                  <table className="w-full text-left text-xs">
                    <thead className="sticky top-0 bg-white/80 backdrop-blur">
                      <tr>
                        <th className="px-3 py-2 font-semibold text-[#66807a]">Trial</th>
                        <th className="px-3 py-2 font-semibold text-[#66807a]">Model</th>
                        <th className="px-3 py-2 font-semibold text-[#66807a]">Extractor</th>
                        <th className="px-3 py-2 font-semibold text-[#66807a]">LR</th>
                        <th className="px-3 py-2 font-semibold text-[#66807a]">Dropout</th>
                        <th className="px-3 py-2 font-semibold text-[#66807a]">Epochs</th>
                        <th className="px-3 py-2 font-semibold text-[#66807a]">Seed</th>
                      </tr>
                    </thead>
                    <tbody>
                      {mcPlan.trials.map((trial) => (
                        <tr key={trial.trial_id} className="border-t border-white/30 hover:bg-[#9cfce0]/5">
                          <td className="px-3 py-2 font-mono text-[#168f8b]">{trial.trial_id.slice(0, 13)}</td>
                          <td className="px-3 py-2 text-[#102b2b]">{trial.mil_model}</td>
                          <td className="px-3 py-2 text-[#102b2b]">{trial.feature_extractor}</td>
                          <td className="px-3 py-2 font-mono text-[#4666d9]">{trial.learning_rate.toExponential(2)}</td>
                          <td className="px-3 py-2 font-mono text-[#7b61ff]">{trial.dropout.toFixed(3)}</td>
                          <td className="px-3 py-2 text-[#102b2b]">{trial.epochs}</td>
                          <td className="px-3 py-2 text-[#8fa9a0]">{trial.seed}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : null}

            {/* Stability-weighted best model */}
            <div className="mt-5 grid gap-4 xl:grid-cols-2">
              {mcStableBest ? (
                <div className="rounded-3xl border border-white/60 bg-white/45 p-4">
                  <div className="mb-3 flex items-center gap-2">
                    <Shield className="h-4 w-4 text-[#168f8b]" />
                    <p className="text-sm font-semibold text-[#102b2b]">
                      Stability-weighted best
                      <span className="ml-2 text-xs font-normal text-[#8fa9a0]">
                        {mcStableBest.total_evaluated} evaluated
                      </span>
                    </p>
                  </div>
                  {mcStableBest.best ? (
                    <div className="grid gap-2">
                      <KeyValue label="Trial" value={mcStableBest.best.trial_id} />
                      <KeyValue label="Stability score" value={mcStableBest.best.stability_score.toFixed(4)} />
                      <KeyValue label="Mean AUROC" value={mcStableBest.best.mean_auroc.toFixed(4)} />
                      <KeyValue label="SD AUROC" value={mcStableBest.best.sd_auroc.toFixed(4)} />
                      <KeyValue label="Model" value={mcStableBest.best.mil_model || "N/A"} />
                      <KeyValue label="Extractor" value={mcStableBest.best.feature_extractor || "N/A"} />
                    </div>
                  ) : (
                    <p className="text-sm text-[#8fa9a0]">No completed trials to rank yet.</p>
                  )}
                  <p className="mt-3 text-xs text-[#66807a]">
                    Formula: {mcStableBest.rank_formula}
                  </p>
                </div>
              ) : null}

              {/* MC Dropout + Bootstrap CI results */}
              <div className="space-y-4">
                {mcDropout?.ok ? (
                  <div className="rounded-3xl border border-white/60 bg-white/45 p-4">
                    <div className="mb-3 flex items-center gap-2">
                      <Sigma className="h-4 w-4 text-[#7b61ff]" />
                      <p className="text-sm font-semibold text-[#102b2b]">MC Dropout uncertainty</p>
                    </div>
                    <div className="grid gap-2">
                      <KeyValue label="Slides" value={String(mcDropout.slide_count)} />
                      <KeyValue label="Passes" value={String(mcDropout.forward_passes)} />
                      <KeyValue label="Mean uncertainty" value={mcDropout.mean_uncertainty.toFixed(4)} />
                    </div>
                    <div className="mt-3 grid grid-cols-3 gap-2">
                      <div className="rounded-2xl border border-[#9cfce0]/30 bg-[#9cfce0]/10 p-2 text-center">
                        <p className="text-lg font-semibold text-[#168f8b]">{mcDropout.high_confidence_pct}%</p>
                        <p className="text-xs text-[#66807a]">High conf</p>
                      </div>
                      <div className="rounded-2xl border border-[#f5c46b]/30 bg-[#f5c46b]/10 p-2 text-center">
                        <p className="text-lg font-semibold text-[#d99a21]">{mcDropout.medium_confidence_pct}%</p>
                        <p className="text-xs text-[#66807a]">Medium</p>
                      </div>
                      <div className="rounded-2xl border border-[#d95d48]/30 bg-[#d95d48]/10 p-2 text-center">
                        <p className="text-lg font-semibold text-[#d95d48]">{mcDropout.low_confidence_pct}%</p>
                        <p className="text-xs text-[#66807a]">Low conf</p>
                      </div>
                    </div>
                  </div>
                ) : null}

                {mcBootstrapCI?.ok ? (
                  <div className="rounded-3xl border border-white/60 bg-white/45 p-4">
                    <div className="mb-3 flex items-center gap-2">
                      <BarChart3 className="h-4 w-4 text-[#4666d9]" />
                      <p className="text-sm font-semibold text-[#102b2b]">
                        Bootstrap CI
                        <span className="ml-2 text-xs font-normal text-[#8fa9a0]">
                          {mcBootstrapCI.n_bootstrap} resamples · {(mcBootstrapCI.ci_level * 100).toFixed(0)}% CI
                        </span>
                      </p>
                    </div>
                    <div className="grid gap-2">
                      {mcBootstrapCI.metrics.map((m) => (
                        <div key={m.metric} className="flex items-center justify-between gap-3 rounded-2xl border border-white/60 bg-white/50 px-3 py-2 text-sm">
                          <span className="font-medium uppercase text-[#66807a]">{m.metric}</span>
                          <span className="font-semibold text-[#102b2b]">
                            {m.point_estimate.toFixed(3)}
                            <span className="ml-1 text-xs font-normal text-[#8fa9a0]">
                              [{m.ci_lower.toFixed(3)} – {m.ci_upper.toFixed(3)}]
                            </span>
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            </div>
          </Panel>

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
    <section
      className="reactive-surface rounded-[1.6rem] border p-4 shadow-xl backdrop-blur-2xl sm:p-5"
      style={{ background: "var(--panel-bg)", borderColor: "var(--panel-border)", boxShadow: "var(--panel-shadow)" }}
    >
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
        <span className="flex h-10 w-10 items-center justify-center rounded-full" style={{ border: "1px solid var(--accent-border)", background: "var(--accent-dim)", color: "var(--tag-text)" }}>
          {icon}
        </span>
        <h2 className="text-xl font-semibold" style={{ color: "var(--heading)" }}>{title}</h2>
      </div>
      <span className="rounded-full border px-3 py-1 text-xs font-semibold uppercase" style={{ borderColor: "var(--border)", background: "var(--btn-bg)", color: "var(--muted)" }}>
        {label}
      </span>
    </div>
  );
}

function Pill({ children, isDark }: { children: React.ReactNode; isDark?: boolean }) {
  return (
    <span
      className="rounded-full border px-3 py-1 text-xs font-semibold shadow-sm"
      style={{
        borderColor: isDark ? "rgba(156,252,224,0.2)" : "rgba(255,255,255,0.7)",
        background: isDark ? "rgba(156,252,224,0.08)" : "rgba(255,255,255,0.45)",
        color: isDark ? "#b7cfc7" : "#36575a",
      }}
    >
      {children}
    </span>
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
      ? "var(--teal)"
      : tone === "blue"
        ? "var(--blue)"
        : "var(--coral)";

  return (
    <div
      className="reactive-surface min-h-28 rounded-[1.4rem] border p-4"
      style={{ borderColor: "var(--card-border)", background: "var(--card-bg)" }}
    >
      <p className="text-sm" style={{ color: "var(--muted)" }}>{label}</p>
      <p className="mt-3 truncate text-3xl font-semibold" style={{ color }}>{value}</p>
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
    <section
      className="reactive-surface rounded-[1.6rem] border p-4 shadow-xl backdrop-blur-2xl sm:p-5"
      style={{ background: "var(--panel-bg)", borderColor: "var(--panel-border)", boxShadow: "var(--panel-shadow)" }}
    >
      <div className="flex items-start gap-3">
        <span className="flex h-10 w-10 items-center justify-center rounded-full" style={{ border: "1px solid var(--accent-border)", background: "var(--accent-dim)", color: "var(--tag-text)" }}>
          {icon}
        </span>
        <div>
          <h2 className="text-base font-semibold" style={{ color: "var(--heading)" }}>{title}</h2>
          <p className="mt-1 text-sm leading-6" style={{ color: "var(--muted)" }}>{description}</p>
        </div>
      </div>

      <label
        className="mt-4 flex min-h-12 cursor-pointer items-center justify-between gap-3 rounded-full border border-dashed px-4 text-sm transition"
        style={{ borderColor: "var(--accent-border)", background: "var(--btn-bg)" }}
      >
        <span className="flex min-w-0 items-center gap-2" style={{ color: "var(--muted)" }}>
          <Upload className="h-4 w-4 shrink-0" />
          <span className="truncate">{fileText}</span>
        </span>
        <span className="shrink-0 rounded-full px-3 py-1 font-semibold" style={{ background: "var(--accent-dim)", color: "var(--tag-text)" }}>
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
      className="reactive-surface inline-flex min-h-11 items-center justify-center gap-2 rounded-full border px-4 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-45"
      style={{ borderColor: "var(--btn-border)", background: "var(--btn-bg)", color: "var(--btn-text)" }}
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
    <div className="reactive-surface rounded-3xl border p-4" style={{ borderColor: "var(--card-border)", background: "var(--card-bg)" }}>
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-semibold" style={{ color: "var(--heading)" }}>{title}</h3>
        <span className="text-sm" style={{ color: "var(--muted)" }}>{columns.length} columns</span>
      </div>
      <div className="mt-4 grid gap-2">
        {Object.entries(detected).map(([field, column]) => (
          <div
            className="flex min-h-10 items-center justify-between gap-3 rounded-2xl border px-3 text-sm"
            style={{ borderColor: "var(--card-border)", background: "var(--card-bg)" }}
            key={field}
          >
            <span className="font-medium capitalize" style={{ color: "var(--muted)" }}>{field}</span>
            <span style={{ color: column ? "var(--teal)" : "var(--coral)" }}>
              {column ?? "Missing"}
            </span>
          </div>
        ))}
      </div>
      {missing.length > 0 ? (
        <p className="mt-3 text-sm leading-6" style={{ color: "var(--warning)" }}>
          Missing required mapping: {missing.join(", ")}.
        </p>
      ) : (
        <p className="mt-3 text-sm leading-6" style={{ color: "var(--teal)" }}>
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
  const data: DistributionDatum[] = entries.map(([label, value], index) => ({
    label,
    value,
    percent: total > 0 ? Math.round((value / total) * 100) : 0,
    fill: chartPalette[index % chartPalette.length],
  }));

  if (entries.length === 0) {
    return <p className="mt-4 text-sm leading-6" style={{ color: "var(--muted)" }}>{emptyText}</p>;
  }

  return (
    <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1fr)_150px]">
      <RechartsDistribution data={data} />
      <div className="space-y-2 lg:col-span-2">
        {data.map((entry) => (
          <div
            className="flex items-center justify-between gap-3 rounded-2xl border px-3 py-2 text-sm"
            style={{ borderColor: "var(--card-border)", background: "var(--card-bg)" }}
            key={entry.label}
          >
            <span className="flex min-w-0 items-center gap-2 font-semibold" style={{ color: "var(--heading)" }}>
              <span
                className="h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ backgroundColor: entry.fill }}
              />
              <span className="truncate">{entry.label}</span>
            </span>
            <span className="shrink-0" style={{ color: "var(--muted)" }}>
              {entry.value.toLocaleString()} ({entry.percent}%)
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ExperimentResult({
  bestExperiment,
  error,
}: {
  bestExperiment?: BestExperiment;
  error: string;
}) {
  const best = bestExperiment?.best;
  const metrics = best?.metrics ?? {};
  const model = readableMetric(metrics.mil_model) || "Waiting for completed run";
  const extractor = readableMetric(metrics.feature_extractor) || "No result yet";
  const epochs = readableMetric(metrics.epochs) || "Pending";
  const folds = Array.isArray(metrics.folds) ? metrics.folds.join(", ") : "Pending";
  const score = best ? best.value.toFixed(4) : "No score";

  return (
    <div className="mt-5 grid gap-4">
      {error ? (
        <p className="rounded-2xl border border-[#d95d48]/30 bg-[#d95d48]/10 p-3 text-sm leading-6" style={{ color: "var(--danger-deep)" }}>
          {error}
        </p>
      ) : null}
      <div className="grid gap-3 sm:grid-cols-3">
        <MetricTile label="Best AUROC" tone="teal" value={score} />
        <MetricTile label="Epochs" tone="blue" value={epochs} />
        <MetricTile label="Completed" tone="coral" value={`${bestExperiment?.completed_trials ?? 0}`} />
      </div>
      <div className="rounded-3xl border p-4" style={{ borderColor: "var(--card-border)", background: "var(--card-bg)" }}>
        <div className="grid gap-3 sm:grid-cols-2">
          <KeyValue label="Best model" value={model} />
          <KeyValue label="Feature extractor" value={extractor} />
          <KeyValue label="Validation folds" value={folds} />
          <KeyValue label="Trial id" value={best?.trial_id ?? "Pending"} />
        </div>
        <p className="mt-4 text-sm leading-6" style={{ color: "var(--muted)" }}>
          Results are selected from VM `metrics.json` files only. If no training
          trial has completed, the dashboard stays pending instead of inventing
          accuracy.
        </p>
      </div>
    </div>
  );
}

function TechSurface({ integrations }: { integrations: IntegrationStatus[] }) {
  const stack = [
    ["UI", "Next.js, React, Tailwind, Three.js, Recharts"],
    ["Charts", "Recharts with D3 data-visualization primitives"],
    ["Automation", "n8n workflows calling FastAPI endpoints"],
    ["Backend", "FastAPI, Pydantic, SSH allowlisted VM actions"],
    ["Training", "Slideflow MIL on pathology310 with NVIDIA L4"],
    ["Data", "GDC TCGA-COAD/READ SVS + cBioPortal MSI labels"],
  ];

  return (
    <div className="mt-5 space-y-4">
      <div className="grid gap-2">
        {stack.map(([label, value]) => (
          <KeyValue key={label} label={label} value={value} />
        ))}
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        {integrations.map((integration) => (
          <div
            className="rounded-2xl border p-3"
            style={{ borderColor: "var(--card-border)", background: "var(--card-bg)" }}
            key={integration.name}
          >
            <div className="flex items-center justify-between gap-3">
              <p className="font-semibold" style={{ color: "var(--heading)" }}>{integration.name}</p>
              <span
                className="rounded-full px-2 py-1 text-xs font-semibold"
                style={{
                  background: integration.configured ? "var(--accent-dim)" : "rgba(217,93,72,0.1)",
                  color: integration.configured ? "var(--teal)" : "var(--coral)",
                }}
              >
                {integration.configured ? "configured" : "missing"}
              </span>
            </div>
            <p className="mt-2 text-xs leading-5" style={{ color: "var(--muted)" }}>
              {integration.use}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

function KeyValue({ label, value }: { label: string; value: string }) {
  return (
    <div
      className="flex min-h-10 items-center justify-between gap-3 rounded-2xl border px-3 text-sm"
      style={{ borderColor: "var(--card-border)", background: "var(--card-bg)" }}
    >
      <span className="shrink-0 font-medium" style={{ color: "var(--muted)" }}>{label}</span>
      <span className="min-w-0 truncate text-right font-semibold" style={{ color: "var(--heading)" }}>
        {value}
      </span>
    </div>
  );
}

function readableMetric(value: unknown) {
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number") {
    return value.toLocaleString();
  }
  return "";
}
