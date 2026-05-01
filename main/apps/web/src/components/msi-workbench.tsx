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
  Layers3,
  Monitor,
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
import {
  Approach1ArtifactCharts,
  Approach2AdvancedCharts,
  MonteCarloAdvancedCharts,
} from "@/components/approach-analytics";
import type { DistributionDatum } from "@/components/recharts-distribution";
import { ParallelResults, type ParallelMetric } from "@/components/parallel-results";

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
type ApproachMode = "approach-1" | "approach-2" | "monte-carlo" | "parallel";

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

type ParallelSourceStatus = {
  name: "Approach1" | "Approach2" | "MonteCarlo";
  ok: boolean;
  source: string;
  message?: string;
  records_found: number;
};

type Approach1Analytics = {
  trial_id: string;
  status: string;
  step: string;
  running: boolean;
  slide_backend: string;
  error: string;
  slides_total: number;
  tfrecord_files: number;
  unfinished_files: number;
  bag_files: number;
  tfrecord_bytes: number;
  bag_bytes: number;
  log_excerpt: string;
};

type Approach2Analytics = {
  runs_total: number;
  completed_runs: number;
  latest_experiment_id: string;
  latest_name: string;
  latest_status: string;
  latest_metrics: Record<string, unknown>;
  history: Array<Record<string, number>>;
  class_distribution: Record<string, number>;
};

type MonteCarloAnalytics = {
  stable_best: StableBestResult["best"] | null;
  total_candidates: number;
  mc_result_trials: number;
  dropout_ready: number;
  bootstrap_ready: number;
};

type DashboardAnalytics = {
  approach1: Approach1Analytics;
  approach2: Approach2Analytics;
  monte_carlo: MonteCarloAnalytics;
  comparison_metrics: ParallelMetric[];
  comparison_sources: ParallelSourceStatus[];
};

type Approach2Experiment = {
  id: number;
  experiment_id: string;
  name: string;
  status: string;
  model_type: string;
  parameters?: Record<string, unknown> | null;
  metrics?: Record<string, unknown> | null;
  created_at: string;
};

type PatchTrainingForm = {
  experimentName: string;
  approachLabel: "Approach1" | "Approach2" | "MonteCarlo";
  datasetSource: "workspace_root" | "custom_path" | "google_bucket";
  workspaceRoot: string;
  datasetPath: string;
  googleBucketUri: string;
  backbone: string;
  epochs: number;
  batchSize: number;
  learningRate: number;
  imageSize: number;
  valSplit: number;
  numWorkers: number;
  selectedExperimentId: string;
};

type UploadPredictionResult = {
  experiment_id: string;
  approach_label: string;
  prediction: string;
  probability: number;
  probabilities: Record<string, number>;
  model_path?: string | null;
};

type TCGASlideTriadLaunchResponse = {
  ok: boolean;
  message: string;
  bundle_id: string;
  experiment_ids: string[];
  remote_status_path: string;
};

type TCGASlideTriadStatusPayload = {
  ok: boolean;
  bundle_id: string;
  remote_status_path: string;
  status: Record<string, unknown>;
};

type LatestTCGASlideTriadStatusPayload = {
  ok: boolean;
  bundle_id: string;
  remote_status_path: string;
  status: Record<string, unknown>;
};

const requiredAnnotationFields = ["patient", "slide", "label", "fold"];
const requiredManifestFields = ["id", "filename"];
const automationApiBase =
  process.env.NEXT_PUBLIC_MSI_API_URL ?? "http://127.0.0.1:8001";
const chartPalette = ["#cbd5e1", "#4666d9", "#d95d48", "#7b61ff", "#d99a21"];
const defaultPatchTrainingForm: PatchTrainingForm = {
  experimentName: "crc-val-he-7k-baseline",
  approachLabel: "Approach2",
  datasetSource: "workspace_root",
  workspaceRoot: "E:\\4basecare-MSI",
  datasetPath: "E:\\4basecare-MSI\\datasets\\CRC-VAL-HE-7K",
  googleBucketUri: "",
  backbone: "resnet18",
  epochs: 10,
  batchSize: 32,
  learningRate: 0.0001,
  imageSize: 224,
  valSplit: 0.2,
  numWorkers: 0,
  selectedExperimentId: "",
};

const tcgaSlideTriadDefaults = {
  experiment_name: "tcga-coad-20-slide-triad",
  bucket_uri: "gs://wsi_aiml_repo/TCGA/TCGA_COAD/TCGA_COAD",
  slide_limit: 18,
  n_folds: 3,
  preferred_slide_pattern: "DX",
  preferred_exact_suffix: "DX1",
  annotations_csv: "annotations/tcga_coad_bucket_annotations_pub.csv",
  feature_extractor: "virchow,uni_v2,uni,phikon,ctranspath,resnet50_imagenet",
  tile_px: 256,
  tile_um: 128,
  max_parallel_approaches: 3,
} as const;

const tcgaBundleStorageKey = "timestamp-msi-latest-tcga-bundle";
const tcgaBundleRefreshSeconds = 30;

function isGoogleBucketUri(value: string) {
  return value.trim().startsWith("gs://");
}

function patchDatasetSourceSummary(form: PatchTrainingForm) {
  if (form.datasetSource === "google_bucket") {
    return form.googleBucketUri.trim() || "gs://your-bucket/path/to/patch-dataset";
  }
  if (form.datasetSource === "workspace_root") {
    return `${form.workspaceRoot}\\datasets\\CRC-VAL-HE-7K`;
  }
  return form.datasetPath.trim() || "Custom local dataset path";
}

const commandBlock = `# Linux VM shell
cd /home/pardeep/pathology310_projects/single_slide_morphology/project_1_slideflow_msi_tcga_crc
pathology310-run python scripts/download_gdc_manifest.py \\
  --manifest annotations/gdc_manifest_tcga_crc_msi.tsv \\
  --out slideflow_project/data/slides

# Jupyter / Antigravity kernel
pathology310-run jupyter lab --ip 127.0.0.1 --port 8888 --no-browser

# Slideflow Studio on VM with X11 forwarding
slideflow-studio
# fallback
python -m slideflow.studio`;

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
  const [approachMode, setApproachMode] = useState<ApproachMode>("approach-1");
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
  const [theme, setTheme] = useState<"dark-theme" | "snow-theme">("snow-theme");
  const isDark = theme === "dark-theme";

  /* Monte Carlo state */
  const [mcPlan, setMcPlan] = useState<MCPlan>();
  const [mcBusy, setMcBusy] = useState<string>();
  const [mcDropout, setMcDropout] = useState<MCDropoutResult>();
  const [mcBootstrapCI, setMcBootstrapCI] = useState<BootstrapCI>();
  const [mcStableBest, setMcStableBest] = useState<StableBestResult>();
  const [mcError, setMcError] = useState("");
  const [mcVmPrep, setMcVmPrep] = useState("");
  const [approach2Experiments, setApproach2Experiments] = useState<Approach2Experiment[]>([]);
  const [approach2Busy, setApproach2Busy] = useState<string>();
  const [approach2Error, setApproach2Error] = useState("");
  const [approach2Message, setApproach2Message] = useState("Approach 2 is ready to register slides or start a pipeline action.");
  const [patchTrainingForm, setPatchTrainingForm] = useState<PatchTrainingForm>(
    defaultPatchTrainingForm,
  );
  const [predictionFile, setPredictionFile] = useState<File>();
  const [predictionResult, setPredictionResult] = useState<UploadPredictionResult>();
  const [tcgaSlideBundleId, setTcgaSlideBundleId] = useState("");
  const [tcgaSlideBundleStatus, setTcgaSlideBundleStatus] = useState<Record<string, unknown>>();
  const [tcgaSlideBundlePath, setTcgaSlideBundlePath] = useState("");
  const [tcgaBundleRefreshIn, setTcgaBundleRefreshIn] = useState(tcgaBundleRefreshSeconds);

  /* Parallel state */
  const [parallelMetrics, setParallelMetrics] = useState<ParallelMetric[]>([]);
  const [parallelSources, setParallelSources] = useState<ParallelSourceStatus[]>([]);
  const [parallelBusy, setParallelBusy] = useState(false);
  const [parallelError, setParallelError] = useState("");
  const [parallelMessage, setParallelMessage] = useState("Parallel Metrics is ready.");
  const [dashboardAnalytics, setDashboardAnalytics] = useState<DashboardAnalytics>();
  const [analyticsError, setAnalyticsError] = useState("");

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

  const latestApproach2Experiment = approach2Experiments[0];
  const latestApproach2Metrics = latestApproach2Experiment?.metrics ?? null;
  const latestApproach2History = Array.isArray(latestApproach2Metrics?.history)
    ? latestApproach2Metrics.history
    : [];
  const hasRunningApproach2Experiment = approach2Experiments.some(
    (experiment) => experiment.status === "running",
  );
  const approach1Analytics = dashboardAnalytics?.approach1;
  const approach2Analytics = dashboardAnalytics?.approach2;
  const monteCarloAnalytics = dashboardAnalytics?.monte_carlo;
  const approachExperimentCounts = useMemo(() => {
    return approach2Experiments.reduce<Record<string, number>>((acc, experiment) => {
      const label = experimentApproachLabel(experiment);
      acc[label] = (acc[label] ?? 0) + 1;
      return acc;
    }, {});
  }, [approach2Experiments]);
  const tcgaBundleState = String(tcgaSlideBundleStatus?.state ?? "");
  const tcgaBundleMatchedSlides = numericMetric(tcgaSlideBundleStatus?.matched_slide_count);
  const tcgaBundleSelectedSlides = numericMetric(tcgaSlideBundleStatus?.selected_slide_count);
  const tcgaBundleDownloadedSlides = numericMetric(tcgaSlideBundleStatus?.downloaded_slide_count);
  const tcgaBundleTfrecordFiles = numericMetric(tcgaSlideBundleStatus?.tfrecord_files);
  const tcgaBundleTfrecordBytes = numericMetric(tcgaSlideBundleStatus?.tfrecord_bytes);
  const tcgaBundleFeatureExtractor = readableMetric(tcgaSlideBundleStatus?.feature_extractor_used) || tcgaSlideTriadDefaults.feature_extractor;
  const tcgaBundleSelectedNames = readStringArray(tcgaSlideBundleStatus?.selected_slides);
  const tcgaBundleRunningApproaches = readStringArray(tcgaSlideBundleStatus?.running_approaches);
  const tcgaBundleCompletedApproaches = readStringArray(tcgaSlideBundleStatus?.completed_approaches);
  const tcgaBundleLabelCounts = (tcgaSlideBundleStatus?.label_counts as Record<string, number> | undefined) ?? {};
  const tcgaBundleApproachSummary = (tcgaSlideBundleStatus?.summary as { approaches?: Record<string, Record<string, unknown>> } | undefined)?.approaches ?? {};
  const tcgaBundleUpdatedAt = numericMetric(tcgaSlideBundleStatus?.updated_at_epoch);
  const tcgaBundleStage = tcgaStageMeta(
    tcgaBundleState,
    tcgaBundleDownloadedSlides,
    tcgaBundleSelectedSlides,
    tcgaBundleCompletedApproaches.length,
    tcgaBundleTfrecordFiles,
  );
  const tcgaBundleStageChart = tcgaStageChart(tcgaBundleState);
  const hasRunningTcgaBundle = Boolean(
    tcgaSlideBundleId &&
      !["", "completed", "failed", "missing", "invalid"].includes(tcgaBundleState),
  );

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const savedBundleId = window.localStorage.getItem(tcgaBundleStorageKey);
    const savedBundlePath = window.localStorage.getItem(`${tcgaBundleStorageKey}:path`);
    if (savedBundleId) {
      setTcgaSlideBundleId(savedBundleId);
    }
    if (savedBundlePath) {
      setTcgaSlideBundlePath(savedBundlePath);
    }
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    if (tcgaSlideBundleId) {
      window.localStorage.setItem(tcgaBundleStorageKey, tcgaSlideBundleId);
    } else {
      window.localStorage.removeItem(tcgaBundleStorageKey);
    }

    if (tcgaSlideBundlePath) {
      window.localStorage.setItem(`${tcgaBundleStorageKey}:path`, tcgaSlideBundlePath);
    } else {
      window.localStorage.removeItem(`${tcgaBundleStorageKey}:path`);
    }
  }, [tcgaSlideBundleId, tcgaSlideBundlePath]);

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

  useEffect(() => {
    let cancelled = false;

    async function refreshAnalytics() {
      try {
        const response = await fetch(`${automationApiBase}/analytics/dashboard`);
        if (!response.ok) {
          throw new Error("Analytics snapshot is not ready.");
        }
        const data = (await response.json()) as DashboardAnalytics;
        if (!cancelled) {
          setDashboardAnalytics(data);
          setAnalyticsError("");
          if (data.comparison_metrics.length > 0) {
            setParallelMetrics(data.comparison_metrics);
          }
          if (data.comparison_sources.length > 0) {
            setParallelSources(data.comparison_sources);
          }
        }
      } catch (error) {
        if (!cancelled) {
          setAnalyticsError(
            error instanceof Error ? error.message : "Unable to load analytics snapshot.",
          );
        }
      }
    }

    void refreshAnalytics();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!approach1Analytics?.running && !hasRunningApproach2Experiment) {
      return;
    }

    const intervalId = window.setInterval(() => {
      void fetch(`${automationApiBase}/analytics/dashboard`)
        .then(async (response) => {
          if (!response.ok) {
            throw new Error("Analytics refresh failed.");
          }
          const data = (await response.json()) as DashboardAnalytics;
          setDashboardAnalytics(data);
          setParallelMetrics(data.comparison_metrics ?? []);
          setParallelSources(data.comparison_sources ?? []);
        })
        .catch((error) => {
          setAnalyticsError(
            error instanceof Error ? error.message : "Analytics refresh failed.",
          );
        });
    }, 12000);

    return () => window.clearInterval(intervalId);
  }, [approach1Analytics?.running, hasRunningApproach2Experiment]);

  useEffect(() => {
    if (approachMode !== "approach-2") {
      return;
    }

    void runApproach2Action("experiments", { silent: approach2Experiments.length > 0 });
    void fetchLatestTcgaSlideTriadStatus({ silent: true });
  }, [approachMode]);

  useEffect(() => {
    if (approachMode !== "approach-2" || !hasRunningApproach2Experiment) {
      return;
    }

    const intervalId = window.setInterval(() => {
      void runApproach2Action("experiments", { silent: true });
    }, 5000);

    return () => window.clearInterval(intervalId);
  }, [approachMode, hasRunningApproach2Experiment]);

  useEffect(() => {
    if (approachMode !== "approach-2" || !tcgaSlideBundleId) {
      return;
    }

    setTcgaBundleRefreshIn(tcgaBundleRefreshSeconds);

    const refreshIntervalId = window.setInterval(() => {
      setTcgaBundleRefreshIn(tcgaBundleRefreshSeconds);
      void fetchTcgaSlideTriadStatus(tcgaSlideBundleId, { silent: true });
    }, tcgaBundleRefreshSeconds * 1000);

    const countdownIntervalId = window.setInterval(() => {
      setTcgaBundleRefreshIn((current) =>
        current <= 1 ? tcgaBundleRefreshSeconds : current - 1,
      );
    }, 1000);

    return () => {
      window.clearInterval(refreshIntervalId);
      window.clearInterval(countdownIntervalId);
    };
  }, [approachMode, tcgaSlideBundleId]);

  useEffect(() => {
    if (approachMode !== "monte-carlo" || mcStableBest || mcBusy) {
      return;
    }

    void fetchStableBest();
  }, [approachMode, mcStableBest, mcBusy]);

  useEffect(() => {
    if (approachMode !== "parallel" || parallelBusy || parallelMetrics.length > 0 || parallelSources.length > 0) {
      return;
    }

    void runParallelPipeline();
  }, [approachMode, parallelBusy, parallelMetrics.length, parallelSources.length]);

  useEffect(() => {
    const root = document.documentElement;
    let frameId = 0;
    let targetX = window.innerWidth * 0.5;
    let targetY = window.innerHeight * 0.35;
    let cursorX = targetX;
    let cursorY = targetY;
    let trailX = targetX;
    let trailY = targetY;

    const updateVars = () => {
      cursorX += (targetX - cursorX) * 0.18;
      cursorY += (targetY - cursorY) * 0.18;
      trailX += (cursorX - trailX) * 0.08;
      trailY += (cursorY - trailY) * 0.08;

      const mx = `${(cursorX / window.innerWidth) * 100}%`;
      const my = `${(cursorY / window.innerHeight) * 100}%`;
      const trailMx = `${(trailX / window.innerWidth) * 100}%`;
      const trailMy = `${(trailY / window.innerHeight) * 100}%`;
      const dx = ((cursorX - window.innerWidth / 2) / window.innerWidth) * 2;
      const dy = ((cursorY - window.innerHeight / 2) / window.innerHeight) * 2;

      root.style.setProperty("--mx", mx);
      root.style.setProperty("--my", my);
      root.style.setProperty("--trail-mx", trailMx);
      root.style.setProperty("--trail-my", trailMy);
      root.style.setProperty("--dx", dx.toFixed(4));
      root.style.setProperty("--dy", dy.toFixed(4));

      frameId = window.requestAnimationFrame(updateVars);
    };

    const handlePointerMove = (event: PointerEvent) => {
      targetX = event.clientX;
      targetY = event.clientY;
    };

    const handleResize = () => {
      targetX = window.innerWidth * 0.5;
      targetY = window.innerHeight * 0.35;
    };

    frameId = window.requestAnimationFrame(updateVars);
    window.addEventListener("pointermove", handlePointerMove, { passive: true });
    window.addEventListener("resize", handleResize);

    return () => {
      window.cancelAnimationFrame(frameId);
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("resize", handleResize);
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
      | "startTunnel"
      | "studioGuide",
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

  async function prepareMCVmWorkspace() {
    setMcBusy("vm-workspace");
    setMcError("");
    setMcVmPrep("");
    try {
      const response = await fetch(`${automationApiBase}/vm/monte-carlo/workspace`, {
        method: "POST",
      });
      const data = (await response.json()) as {
        ok: boolean;
        stdout?: string;
        stderr?: string;
        error?: string;
      };

      if (!response.ok || !data.ok) {
        throw new Error(data.error || data.stderr || "VM Monte Carlo prep failed.");
      }

      setMcVmPrep([data.stdout, data.stderr].filter(Boolean).join("\n\n") || "VM workspace prepared.");
    } catch (error) {
      setMcError(error instanceof Error ? error.message : "VM Monte Carlo prep failed.");
    } finally {
      setMcBusy(undefined);
    }
  }

  function buildPatchPayload(overrides: Partial<Record<string, unknown>> = {}) {
    return {
      experiment_name: patchTrainingForm.experimentName,
      training_mode: "patch_classification",
      approach_label: patchTrainingForm.approachLabel,
      dataset_source: patchTrainingForm.datasetSource,
      workspace_root: patchTrainingForm.workspaceRoot,
      dataset_path: patchTrainingForm.datasetPath,
      google_bucket_uri: patchTrainingForm.googleBucketUri || null,
      backbone: patchTrainingForm.backbone,
      epochs: patchTrainingForm.epochs,
      batch_size: patchTrainingForm.batchSize,
      learning_rate: patchTrainingForm.learningRate,
      image_size: patchTrainingForm.imageSize,
      val_split: patchTrainingForm.valSplit,
      num_workers: patchTrainingForm.numWorkers,
      seed: 310,
      use_pretrained: true,
      ...overrides,
    };
  }

  function applyTriadPreset(label: "Approach1" | "Approach2" | "MonteCarlo") {
    const presets: Record<typeof label, Partial<PatchTrainingForm>> = {
      Approach1: {
        approachLabel: "Approach1",
        experimentName: "crc-triad-approach1",
        backbone: "resnet34",
        epochs: 5,
      },
      Approach2: {
        approachLabel: "Approach2",
        experimentName: "crc-triad-approach2",
        backbone: "resnet18",
        epochs: 10,
      },
      MonteCarlo: {
        approachLabel: "MonteCarlo",
        experimentName: "crc-triad-approach3",
        backbone: "resnet18",
        epochs: 4,
      },
    };
    setPatchTrainingForm((current) => ({
      ...current,
      ...presets[label],
    }));
  }

  async function runPresetTraining(label: "Approach1" | "Approach2" | "MonteCarlo") {
    const presets: Record<typeof label, Partial<Record<string, unknown>>> = {
      Approach1: {
        experiment_name: "crc-triad-approach1",
        approach_label: "Approach1",
        backbone: "resnet34",
        epochs: 5,
      },
      Approach2: {
        experiment_name: "crc-triad-approach2",
        approach_label: "Approach2",
        backbone: "resnet18",
        epochs: 10,
      },
      MonteCarlo: {
        experiment_name: "crc-triad-approach3",
        approach_label: "MonteCarlo",
        backbone: "resnet18",
        epochs: 4,
      },
    };
    applyTriadPreset(label);
    await runApproach2Action("train", undefined, presets[label]);
  }

  async function runApproach2Action(
    action: "preprocess" | "features" | "train" | "triad" | "experiments",
    options?: { silent?: boolean },
    payloadOverrides?: Partial<Record<string, unknown>>,
  ) {
    if (
      (action === "train" || action === "triad") &&
      patchTrainingForm.datasetSource === "google_bucket" &&
      !isGoogleBucketUri(patchTrainingForm.googleBucketUri)
    ) {
      setApproach2Error("Enter a valid Google bucket URI like gs://my-bucket/path before starting training.");
      return;
    }

    setApproach2Busy(action);
    if (!options?.silent) {
      setApproach2Error("");
    }

    const requests: Record<typeof action, { path: string; body?: Record<string, unknown> }> = {
      preprocess: {
        path: "/approach-2/pipeline/preprocess",
        body: { cohort: "default", tile_size: 256, tile_um: 256 },
      },
      features: {
        path: "/approach-2/pipeline/extract_features",
        body: { cohort: "default", feature_extractor: "resnet50" },
      },
      train: {
        path: "/approach-2/pipeline/train",
        body: buildPatchPayload(payloadOverrides),
      },
      triad: {
        path: "/approach-2/pipeline/train-triad",
        body: buildPatchPayload({
          experiment_name: patchTrainingForm.experimentName || "crc-complex-triad",
          ...payloadOverrides,
        }),
      },
      experiments: { path: "/approach-2/experiments/" },
    };

    try {
      const request = requests[action];
      const response = await fetch(`${automationApiBase}${request.path}`, {
        method: request.body ? "POST" : "GET",
        headers: request.body ? { "Content-Type": "application/json" } : undefined,
        body: request.body ? JSON.stringify(request.body) : undefined,
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data?.detail || "Approach 2 request failed.");
      }

      if (action === "experiments") {
        const experiments = Array.isArray(data) ? (data as Approach2Experiment[]) : [];
        setApproach2Experiments(experiments);
        const counts = experiments.reduce<Record<string, number>>((acc, experiment) => {
          const label = experimentApproachLabel(experiment);
          acc[label] = (acc[label] ?? 0) + 1;
          return acc;
        }, {});

        const runningCount = experiments.filter(
          (experiment) => experiment.status === "running",
        ).length;
        const latest = experiments[0];
        const accuracy = readableMetric(latest?.metrics?.best_val_accuracy);
        const epochCount = Array.isArray(latest?.metrics?.history)
          ? latest.metrics.history.length
          : 0;
        setApproach2Message(
          [
            `Loaded ${experiments.length} triad experiment records.`,
            `Approach1=${counts.Approach1 ?? 0} | Approach2=${counts.Approach2 ?? 0} | Approach3=${counts.MonteCarlo ?? 0}`,
            runningCount > 0 ? `${runningCount} run(s) still training.` : "",
            latest
              ? `Latest: ${latest.name} | status=${latest.status} | accuracy=${accuracy || "pending"} | epochs=${epochCount || "pending"}`
              : "",
          ]
            .filter(Boolean)
            .join("\n"),
        );
      } else if (action === "train") {
        setApproach2Message(
          patchTrainingForm.datasetSource === "google_bucket"
            ? `Started ${patchTrainingForm.approachLabel} VM patch run ${data.experiment_id ?? ""} from ${patchTrainingForm.googleBucketUri}. The VM will stage the bucket dataset into a per-run folder and train from there.`
            : `Started ${patchTrainingForm.approachLabel} patch run ${data.experiment_id ?? ""} using ${patchDatasetSourceSummary(patchTrainingForm)}.`,
        );
        void runApproach2Action("experiments", { silent: true });
      } else if (action === "triad") {
        setApproach2Message(
          patchTrainingForm.datasetSource === "google_bucket"
            ? `Queued full complex triad on the VM from ${patchTrainingForm.googleBucketUri}. Experiments: ${(data.experiment_ids ?? []).join(", ")}`
            : `Queued full complex triad on the VM. Experiments: ${(data.experiment_ids ?? []).join(", ")}`,
        );
        void runApproach2Action("experiments", { silent: true });
      } else {
        setApproach2Message(JSON.stringify(data, null, 2));
      }
    } catch (error) {
      if (!options?.silent) {
        setApproach2Error(error instanceof Error ? error.message : "Approach 2 request failed.");
      }
    } finally {
      setApproach2Busy(undefined);
    }
  }

  async function fetchTcgaSlideTriadStatus(
    bundleId: string,
    options?: { silent?: boolean },
  ) {
    try {
      const response = await fetch(
        `${automationApiBase}/approach-2/pipeline/train-tcga-slide-triad/${bundleId}`,
      );
      const data = (await response.json()) as TCGASlideTriadStatusPayload;
      if (!response.ok) {
        throw new Error("Unable to read TCGA slide triad status.");
      }
      const state = String(data.status?.state ?? "queued");
      if (state === "missing" || state === "invalid") {
        return await fetchLatestTcgaSlideTriadStatus({
          silent: options?.silent,
          preferredBundleId: bundleId,
        });
      }
      setTcgaSlideBundleId(bundleId);
      setTcgaSlideBundleStatus(data.status ?? {});
      setTcgaSlideBundlePath(data.remote_status_path ?? "");
      setTcgaBundleRefreshIn(tcgaBundleRefreshSeconds);
      if (!options?.silent) {
        setApproach2Message(
          `TCGA slide triad ${bundleId} is ${state}. Status file: ${data.remote_status_path}`,
        );
      }
      return data;
    } catch (error) {
      if (!options?.silent) {
        setApproach2Error(
          error instanceof Error ? error.message : "Unable to read TCGA slide triad status.",
        );
      }
      return undefined;
    }
  }

  async function fetchLatestTcgaSlideTriadStatus(
    options?: { silent?: boolean; preferredBundleId?: string },
  ) {
    try {
      const response = await fetch(
        `${automationApiBase}/approach-2/pipeline/train-tcga-slide-triad-latest`,
      );
      const data = (await response.json()) as LatestTCGASlideTriadStatusPayload;
      if (!response.ok) {
        throw new Error("Unable to read the latest TCGA slide triad status.");
      }

      const latestBundleId = String(data.bundle_id ?? "");
      const latestState = String(data.status?.state ?? "");
      if (!latestBundleId) {
        if (!options?.silent) {
          setApproach2Message("No TCGA slide triad bundle is available on the VM yet.");
        }
        return data;
      }

      setTcgaSlideBundleId(latestBundleId);
      setTcgaSlideBundleStatus(data.status ?? {});
      setTcgaSlideBundlePath(data.remote_status_path ?? "");
      setTcgaBundleRefreshIn(tcgaBundleRefreshSeconds);
      if (!options?.silent) {
        const sourceNote =
          options?.preferredBundleId && options.preferredBundleId !== latestBundleId
            ? ` Switched from stale bundle ${options.preferredBundleId} to latest bundle ${latestBundleId}.`
            : "";
        setApproach2Message(
          `Latest TCGA slide triad ${latestBundleId} is ${latestState || "queued"}.${sourceNote} Status file: ${data.remote_status_path}`,
        );
      }
      return data;
    } catch (error) {
      if (!options?.silent) {
        setApproach2Error(
          error instanceof Error
            ? error.message
            : "Unable to read the latest TCGA slide triad status.",
        );
      }
      return undefined;
    }
  }

  async function runTcgaSlideTriad() {
    setApproach2Busy("tcga-triad");
    setApproach2Error("");
    setTcgaSlideBundleStatus(undefined);
    try {
      const response = await fetch(
        `${automationApiBase}/approach-2/pipeline/train-tcga-slide-triad`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(tcgaSlideTriadDefaults),
        },
      );
      const data = (await response.json()) as TCGASlideTriadLaunchResponse;
      if (!response.ok) {
        throw new Error(data?.message || "Unable to launch TCGA slide triad.");
      }

      setTcgaSlideBundleId(data.bundle_id);
      setTcgaSlideBundlePath(data.remote_status_path);
      setTcgaBundleRefreshIn(tcgaBundleRefreshSeconds);
      setApproach2Message(
        `${data.message} Bundle ${data.bundle_id} | Experiments: ${data.experiment_ids.join(", ")}`,
      );
      await fetchTcgaSlideTriadStatus(data.bundle_id, { silent: true });
      void runApproach2Action("experiments", { silent: true });
    } catch (error) {
      setApproach2Error(
        error instanceof Error ? error.message : "Unable to launch TCGA slide triad.",
      );
    } finally {
      setApproach2Busy(undefined);
    }
  }

  async function runUploadedPrediction() {
    if (!predictionFile) {
      setApproach2Error("Choose a patch image to predict first.");
      return;
    }

    setApproach2Busy("predict-upload");
    setApproach2Error("");
    setPredictionResult(undefined);
    try {
      const formData = new FormData();
      formData.append("file", predictionFile);
      formData.append("approach_label", patchTrainingForm.approachLabel);
      if (patchTrainingForm.selectedExperimentId) {
        formData.append("experiment_id", patchTrainingForm.selectedExperimentId);
      }

      const response = await fetch(`${automationApiBase}/approach-2/pipeline/predict-upload`, {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.detail || "Prediction upload failed.");
      }
      setPredictionResult(data as UploadPredictionResult);
      setApproach2Message(
        `Prediction complete for ${predictionFile.name}: ${data.prediction} (${readableMetric(data.probability)})`,
      );
    } catch (error) {
      setApproach2Error(error instanceof Error ? error.message : "Prediction upload failed.");
    } finally {
      setApproach2Busy(undefined);
    }
  }

  async function runParallelPipeline() {
    setParallelBusy(true);
    setParallelError("");
    setParallelMetrics([]);
    setParallelSources([]);
    setParallelMessage("Starting real metrics snapshot...");
    try {
      const response = await fetch(`${automationApiBase}/parallel-pipeline/start`, { method: "POST" });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.detail || "Parallel metrics snapshot failed to start.");
      }
      setParallelMessage(data.message || `Snapshot queued with ID: ${data.execution_id}`);

      const pollMetrics = async (attempt = 0) => {
        const metricsRes = await fetch(`${automationApiBase}/parallel-pipeline/metrics/${data.execution_id}`);
        const metricsData = await metricsRes.json();
        if (!metricsRes.ok) {
          throw new Error(metricsData?.detail || "Unable to read parallel metrics.");
        }

        setParallelMetrics(metricsData.metrics || []);
        setParallelSources(metricsData.sources || []);
        const sourceSummary = Array.isArray(metricsData.sources)
          ? metricsData.sources
              .map((source: { name: string; ok: boolean; records_found: number; message?: string }) =>
                `${source.name}: ${source.ok ? source.records_found : "error"}`
              )
              .join(" | ")
          : "";
        setParallelMessage([metricsData.message, sourceSummary].filter(Boolean).join("\n"));

        if ((metricsData.status === "pending" || metricsData.status === "running") && attempt < 20) {
          window.setTimeout(() => {
            void pollMetrics(attempt + 1).catch((error) => {
              setParallelError(error instanceof Error ? error.message : "Parallel metrics polling failed.");
              setParallelBusy(false);
            });
          }, 1500);
          return;
        }

        setParallelBusy(false);
      };

      await pollMetrics();
    } catch (error) {
      setParallelError(error instanceof Error ? error.message : "Parallel metrics snapshot failed.");
      setParallelBusy(false);
    }
  }

  return (
    <main className={`${theme} min-h-screen overflow-hidden`} style={{ background: "var(--background)", color: "var(--foreground)" }}>
      <img
        aria-hidden="true"
        className="pointer-events-none fixed inset-0 z-0 h-full w-full object-cover"
        src="/assets/4basecare-mars.png"
        alt=""
        style={{
          filter: isDark ? "grayscale(0.72) saturate(0.42) brightness(0.55) contrast(1.12)" : "saturate(0.55) brightness(1.2) contrast(0.82)",
          opacity: isDark ? 0.12 : 0.28,
        }}
      />
      <div className="snow-video-veil" />
      <div className="mouse-aura" />
      <div className="sky-sparkle-field" />
      {isDark ? (
        <div className="pointer-events-none fixed inset-0 bg-[linear-gradient(115deg,rgba(255,255,255,0.055),transparent_42%),linear-gradient(245deg,rgba(148,163,184,0.095),transparent_36%),radial-gradient(circle_at_50%_-10%,rgba(226,232,240,0.08),transparent_34%)]" />
      ) : (
        <div className="pointer-events-none fixed inset-0 bg-[linear-gradient(115deg,rgba(255,255,255,0.82),transparent_42%),linear-gradient(245deg,rgba(176,223,255,0.34),transparent_36%),radial-gradient(circle_at_50%_-10%,rgba(255,255,255,0.78),transparent_34%)]" />
      )}
      <div className="pointer-events-none fixed inset-0 bg-[linear-gradient(rgba(148,163,184,0.065)_1px,transparent_1px),linear-gradient(90deg,rgba(148,163,184,0.065)_1px,transparent_1px)] bg-[size:72px_72px] opacity-45" />
      <section className="relative z-10 mx-auto flex min-h-[92vh] w-full max-w-[1500px] flex-col px-4 pb-8 pt-4 sm:px-6 lg:px-8">
        <header className="flex min-h-14 items-center justify-between border-b border-white/10">
          <div className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-full border" style={{ borderColor: "var(--accent-border)", background: "var(--accent-dim)", color: "var(--tag-text)" }}>
              <FlaskConical className="h-4 w-4" />
            </span>
            <div>
              <p className="text-sm font-semibold" style={{ color: "var(--heading)" }}>Timestamp_msi</p>
              <p className="text-xs" style={{ color: "var(--muted)" }}>MSI-H / MSS command surface</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="hidden rounded-full border p-1 sm:flex" style={{ borderColor: "var(--border)", background: "var(--btn-bg)" }}>
              {(["approach-1", "approach-2", "monte-carlo", "parallel"] as ApproachMode[]).map((mode) => (
                <button
                  className="rounded-full px-3 py-1.5 text-xs font-semibold transition"
                  key={mode}
                  onClick={() => setApproachMode(mode)}
                  style={{
                    background: approachMode === mode ? "var(--accent-dim)" : "transparent",
                    color: approachMode === mode ? "var(--tag-text)" : "var(--muted)",
                  }}
                  type="button"
                >
                  {mode === "approach-1" ? "Approach 1" : mode === "approach-2" ? "Approach 2" : mode === "monte-carlo" ? "Monte Carlo" : "Parallel Metrics"}
                </button>
              ))}
            </div>
            <div className="hidden items-center gap-2 md:flex">
              <Pill isDark={isDark}>TCGA CRC</Pill>
              <Pill isDark={isDark}>SVS: batch 10</Pill>
              <Pill isDark={isDark}>VM L4</Pill>
            </div>
            <button
              className="flex h-9 w-9 items-center justify-center rounded-full border transition-colors"
              style={{
                borderColor: isDark ? "rgba(226,232,240,0.34)" : "rgba(255,255,255,0.7)",
                background: isDark ? "rgba(226,232,240,0.11)" : "rgba(255,255,255,0.5)",
                color: isDark ? "#f1f5f9" : "#143536",
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
            <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(320px,460px)] lg:items-center">
              <div className="max-w-3xl">
                <div className="mb-6 flex flex-wrap items-center gap-2">
                  <span className="rounded-full px-3 py-1 text-xs font-semibold uppercase" style={{ border: "1px solid var(--accent-border)", background: "var(--accent-dim)", color: "var(--tag-text)" }}>
                    Bio-control room
                  </span>
                  <span className="rounded-full border px-3 py-1 text-xs" style={{ borderColor: "var(--border)", background: "var(--btn-bg)", color: "var(--muted)" }}>
                    {approachMode === "approach-1"
                      ? "local UI + VM pipeline"
                      : approachMode === "approach-2"
                        ? "Slideflow platform API"
                        : approachMode === "monte-carlo"
                          ? "VM Monte Carlo + AI providers"
                          : "Artifact metrics"}
                  </span>
                </div>
                <h1 className="hover-sentence max-w-4xl text-5xl font-semibold leading-[0.94] sm:text-7xl lg:text-6xl 2xl:text-8xl" style={{ color: "var(--heading)" }}>
                  {approachMode === "approach-1"
                    ? "MSI slide intelligence, live from the VM."
                    : approachMode === "approach-2"
                      ? "Switchable MSI platform, from cohort to model registry."
                      : approachMode === "monte-carlo"
                        ? "Monte Carlo as a dedicated validation approach."
                        : "Parallel artifact metrics, only when runs exist."}
                </h1>
                <p className="hover-sentence mt-6 max-w-2xl text-base leading-8 sm:text-lg" style={{ color: "var(--body)" }}>
                  {approachMode === "approach-1"
                    ? "Upload cohort files, check fold balance, inspect the remote slide project, and launch Jupyter without leaving the browser."
                    : approachMode === "approach-2"
                      ? "Register slides, trigger preprocessing, extract features, train Attention MIL, and review Approach 2 experiments from the same control room."
                      : approachMode === "monte-carlo"
                        ? "Generate stochastic trial plans, prepare the VM model cache, use HF model storage, and check Groq, Firecrawl, Zerve, and Tinyfish readiness."
                        : "Read completed Approach 1, Approach 2, and Monte Carlo artifacts, then compare only the metrics the backend actually finds."}
                </p>
              </div>

              <div className="research-video-wrap">
                <img
                  aria-label="Researching cancer MSI-H image"
                  className="h-full w-full object-cover"
                  src="/assets/4basecare-mars.png"
                  alt="4basecare mars"
                />
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              <MetricTile
                label={approachMode === "approach-1" ? "Annotation rows" : approachMode === "approach-2" ? "Approach 2 runs" : "MC trials"}
                value={approachMode === "approach-1" ? usableAnnotationRows.toLocaleString() : approachMode === "approach-2" ? approach2Experiments.length.toLocaleString() : String(mcPlan?.trial_count ?? 0)}
                tone="teal"
              />
              <MetricTile
                label={approachMode === "approach-1" ? "Manifest rows" : approachMode === "approach-2" ? "Pipeline API" : "VM cache"}
                value={approachMode === "approach-1" ? usableManifestRows.toLocaleString() : approachMode === "approach-2" ? (approach2Busy ? "Running" : "Ready") : mcVmPrep ? "Prepared" : "Pending"}
                tone="blue"
              />
              <MetricTile
                label={approachMode === "approach-1" ? "VM state" : approachMode === "approach-2" ? "Monte Carlo" : "AI links"}
                value={approachMode === "approach-1" ? (vmBusy ? "Running" : readyChecks ? "Ready" : "Standby") : approachMode === "approach-2" ? (mcPlan ? `${mcPlan.trial_count} trials` : "Integrated") : `${integrations.filter((item) => item.configured).length}/${integrations.length}`}
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

      <section className={`relative z-10 mx-auto w-full max-w-[1500px] gap-5 px-4 pb-10 sm:px-6 lg:px-8 xl:grid-cols-[420px_minmax(0,1fr)] ${approachMode === "approach-1" ? "grid" : "hidden"}`}>
        <aside className="space-y-5">
          <Panel>
            <SectionTitle
              icon={<Server className="h-5 w-5" />}
              title="VM run block"
              label="editable"
            />
            <textarea
              className="mt-4 min-h-64 w-full resize-y rounded-2xl border border-[#3a404a] bg-[#0b0d10] p-4 font-mono text-xs leading-5 text-[#edf1f7] outline-none ring-0 transition focus:border-[#e5e7eb]/60"
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
                <ActionButton
                  busy={vmBusy === "studioGuide"}
                  disabled={Boolean(vmBusy)}
                  icon={<Monitor className="h-4 w-4" />}
                  label="Studio guide"
                  onClick={() => runVmAction("studioGuide")}
                />
                <a
                  className="inline-flex min-h-11 items-center justify-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 text-sm font-semibold text-[#ecfff8] transition hover:border-[#e5e7eb]/50 hover:bg-[#e5e7eb]/10"
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
                <pre className="max-h-80 min-h-52 overflow-auto rounded-3xl border border-[#3a404a] bg-[#0b0d10] p-4 text-xs leading-5 text-[#edf1f7] shadow-inner shadow-black/70">
                  {vmError || vmOutput}
                </pre>
                <p className="mt-3 text-sm leading-6" style={{ color: "var(--muted)" }}>
                  Slideflow Studio is integrated here as a launch guide because it is a desktop GUI. Use the
                  `Studio guide` button to print the exact VM/X11 commands and project paths for this repo.
                </p>
              </div>

              <div>
                <p className="mb-2 text-sm font-medium text-[#8fa9a0]">
                  VM files
                </p>
                <div className="max-h-80 overflow-auto rounded-3xl border border-[#3a404a] bg-[#111318]">
                  {vmFiles.length > 0 ? (
                    vmFiles.map((file) => (
                      <button
                        className="flex w-full items-center justify-between gap-3 border-b border-white/5 px-4 py-3 text-left text-sm transition last:border-b-0 hover:bg-[#e5e7eb]/8"
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
                          <span className="block truncate font-medium text-[#f3f5f8]">
                            {file.name}
                          </span>
                          <span className="text-xs text-[#8fa9a0]">
                            {file.modified}
                          </span>
                        </span>
                        <span className="shrink-0 rounded-full border border-white/10 px-2 py-1 text-xs text-[#c6ccd5]">
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
                      ? "border-[#e5e7eb]/40 bg-[#e5e7eb]/10 text-[#e5e7eb]"
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

          <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
            <Panel>
              <SectionTitle
                icon={<BarChart3 className="h-5 w-5" />}
                title="Approach 1 analytics"
                label={approach1Analytics?.running ? "live" : approach1Analytics?.status ?? "idle"}
              />
              <div className="mt-5 grid gap-3 sm:grid-cols-4">
                <MetricTile label="Slides" tone="teal" value={String(approach1Analytics?.slides_total ?? 0)} />
                <MetricTile label="TFRecords" tone="blue" value={String(approach1Analytics?.tfrecord_files ?? 0)} />
                <MetricTile label="Unfinished" tone="coral" value={String(approach1Analytics?.unfinished_files ?? 0)} />
                <MetricTile label="Bags" tone="blue" value={String(approach1Analytics?.bag_files ?? 0)} />
              </div>
              <div className="mt-4 grid gap-2 sm:grid-cols-2">
                <KeyValue label="Trial" value={approach1Analytics?.trial_id || "pending"} />
                <KeyValue label="Status" value={approach1Analytics?.status || "idle"} />
                <KeyValue label="Step" value={approach1Analytics?.step || "pending"} />
                <KeyValue label="Slide backend" value={approach1Analytics?.slide_backend || "unknown"} />
              </div>
              <div className="mt-5">
                <Approach1ArtifactCharts
                  snapshot={{
                    slides_total: approach1Analytics?.slides_total ?? 0,
                    tfrecord_files: approach1Analytics?.tfrecord_files ?? 0,
                    unfinished_files: approach1Analytics?.unfinished_files ?? 0,
                    bag_files: approach1Analytics?.bag_files ?? 0,
                    tfrecord_bytes: approach1Analytics?.tfrecord_bytes ?? 0,
                    bag_bytes: approach1Analytics?.bag_bytes ?? 0,
                  }}
                />
              </div>
            </Panel>

            <Panel>
              <SectionTitle
                icon={<ClipboardList className="h-5 w-5" />}
                title="Extraction log"
                label={approach1Analytics?.error ? "warning" : "tail"}
              />
              <pre className="mt-5 min-h-80 overflow-auto rounded-3xl border p-4 text-xs leading-5" style={{ borderColor: "var(--input-border)", background: "var(--input-bg)", color: approach1Analytics?.error ? "var(--danger)" : "var(--input-text)" }}>
                {approach1Analytics?.error || approach1Analytics?.log_excerpt || analyticsError || "Approach 1 log will appear here once the VM snapshot is available."}
              </pre>
            </Panel>
          </section>

          <div className="hidden">
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
                  <BarChart3 className="h-4 w-4 text-[#e5e7eb]" />
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
                        <tr key={trial.trial_id} className="border-t border-white/30 hover:bg-[#e5e7eb]/5">
                          <td className="px-3 py-2 font-mono text-[#cbd5e1]">{trial.trial_id.slice(0, 13)}</td>
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
                    <Shield className="h-4 w-4 text-[#cbd5e1]" />
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
                      <div className="rounded-2xl border border-[#e5e7eb]/30 bg-[#e5e7eb]/10 p-2 text-center">
                        <p className="text-lg font-semibold text-[#cbd5e1]">{mcDropout.high_confidence_pct}%</p>
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
          </div>

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
                      <p className="mt-1 text-xs font-semibold uppercase text-[#d1d5db]">
                        {stage.owner}
                      </p>
                    </div>
                    <span className="rounded-full border border-white/10 px-2 py-1 text-xs text-[#c6ccd5]">
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

      <section className={`relative z-10 mx-auto w-full max-w-[1500px] gap-5 px-4 pb-10 sm:px-6 lg:px-8 ${approachMode === "approach-2" ? "grid" : "hidden"}`}>
        <Panel>
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <SectionTitle
              icon={<Activity className="h-5 w-5" />}
              title="TCGA background runner"
              label={tcgaBundleStage.label}
            />
            <div className="grid gap-2 sm:grid-cols-2 lg:min-w-[420px]">
              <ActionButton
                busy={approach2Busy === "tcga-triad"}
                disabled={Boolean(approach2Busy)}
                icon={<Database className="h-4 w-4" />}
                label="Run TCGA Adaptive"
                onClick={() => void runTcgaSlideTriad()}
              />
              <ActionButton
                busy={approach2Busy === "experiments"}
                disabled={Boolean(approach2Busy) || !tcgaSlideBundleId}
                icon={<RefreshCw className="h-4 w-4" />}
                label="Refresh bundle"
                onClick={() => {
                  if (tcgaSlideBundleId) {
                    void fetchTcgaSlideTriadStatus(tcgaSlideBundleId);
                  }
                }}
              />
            </div>
          </div>

          <div className="mt-5 overflow-hidden rounded-[28px] border" style={{ borderColor: "var(--card-border)", background: "var(--card-bg)" }}>
            <div className="h-3 w-full" style={{ background: "var(--btn-bg)" }}>
              <div
                className="h-full rounded-r-full transition-all duration-500"
                style={{
                  width: `${tcgaBundleStage.percent}%`,
                  background:
                    tcgaBundleState === "failed"
                      ? "linear-gradient(90deg, rgba(217,93,72,0.95), rgba(217,93,72,0.55))"
                      : "linear-gradient(90deg, rgba(70,102,217,0.95), rgba(122,215,255,0.88))",
                }}
              />
            </div>
            <div className="grid gap-4 p-5 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)]">
              <div>
                <div className="flex flex-wrap items-center gap-3">
                  <span className="rounded-full border px-3 py-1 text-xs font-semibold" style={{ borderColor: "var(--accent-border)", background: "var(--accent-dim)", color: "var(--tag-text)" }}>
                    {tcgaBundleStage.percent}% complete
                  </span>
                  <span className="rounded-full border px-3 py-1 text-xs font-semibold" style={{ borderColor: "var(--border)", background: "var(--btn-bg)", color: "var(--heading)" }}>
                    Auto-refresh every 30s
                  </span>
                  <span className="text-sm font-semibold" style={{ color: "var(--heading)" }}>
                    {tcgaBundleStage.title}
                  </span>
                  <span className="text-sm" style={{ color: "var(--muted)" }}>
                    {tcgaBundleState ? `State: ${tcgaBundleState}` : "No active bundle yet"}
                  </span>
                </div>
                <p className="mt-3 text-sm leading-6" style={{ color: "var(--body)" }}>
                  {tcgaBundleStage.detail}
                </p>
                <div className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
                  <KeyValue label="Bundle ID" value={tcgaSlideBundleId || "Not started"} />
                  <KeyValue label="Selected" value={tcgaBundleSelectedSlides !== undefined ? String(tcgaBundleSelectedSlides) : "Pending"} />
                  <KeyValue label="Downloaded" value={tcgaBundleDownloadedSlides !== undefined ? String(tcgaBundleDownloadedSlides) : "Pending"} />
                  <KeyValue label="TFRecords" value={tcgaBundleTfrecordFiles !== undefined ? String(tcgaBundleTfrecordFiles) : "Pending"} />
                  <KeyValue label="TFRecord size" value={tcgaBundleTfrecordBytes !== undefined ? formatBytes(tcgaBundleTfrecordBytes) : "Pending"} />
                  <KeyValue label="Next refresh" value={tcgaSlideBundleId ? `${tcgaBundleRefreshIn}s` : "Waiting"} />
                  <KeyValue label="Updated" value={tcgaBundleUpdatedAt ? formatEpochTime(tcgaBundleUpdatedAt) : "Waiting"} />
                </div>
                <div className="mt-5 rounded-3xl border p-4" style={{ borderColor: "var(--border)", background: "var(--btn-bg)" }}>
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <h3 className="text-sm font-semibold" style={{ color: "var(--heading)" }}>Stage chart</h3>
                    <span className="text-xs" style={{ color: "var(--muted)" }}>
                      Live pipeline checkpoints
                    </span>
                  </div>
                  <div className="grid gap-3 md:grid-cols-6">
                    {tcgaBundleStageChart.map((stage) => (
                      <div key={stage.key} className="relative">
                        <div
                          className="rounded-3xl border px-3 py-3"
                          style={{
                            borderColor: stage.isCurrent
                              ? "var(--accent-border)"
                              : stage.isDone
                                ? "rgba(44,182,125,0.35)"
                                : "var(--border)",
                            background: stage.isCurrent
                              ? "var(--accent-dim)"
                              : stage.isDone
                                ? "rgba(44,182,125,0.08)"
                                : "var(--card-bg)",
                          }}
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-xs font-semibold uppercase tracking-[0.16em]" style={{ color: stage.isCurrent ? "var(--tag-text)" : stage.isDone ? "var(--teal)" : "var(--muted)" }}>
                              {stage.short}
                            </span>
                            <span
                              className="h-2.5 w-2.5 rounded-full"
                              style={{
                                background: stage.isCurrent
                                  ? "var(--tag-text)"
                                  : stage.isDone
                                    ? "var(--teal)"
                                    : "rgba(148,163,184,0.45)",
                              }}
                            />
                          </div>
                          <p className="mt-2 text-sm font-semibold" style={{ color: "var(--heading)" }}>
                            {stage.title}
                          </p>
                          <p className="mt-1 text-xs" style={{ color: "var(--muted)" }}>
                            {stage.isCurrent ? "Running now" : stage.isDone ? "Done" : "Waiting"}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              <div className="rounded-3xl border p-4" style={{ borderColor: "var(--border)", background: "var(--btn-bg)" }}>
                <h3 className="text-sm font-semibold" style={{ color: "var(--heading)" }}>Dedicated live summary</h3>
                <div className="mt-3 grid gap-2">
                  <KeyValue label="Extractor" value={tcgaBundleFeatureExtractor || "Pending"} />
                  <KeyValue
                    label="Labels"
                    value={
                      Object.keys(tcgaBundleLabelCounts).length > 0
                        ? Object.entries(tcgaBundleLabelCounts).map(([key, value]) => `${key} ${value}`).join(" | ")
                        : "Pending"
                    }
                  />
                  <KeyValue
                    label="Running"
                    value={tcgaBundleRunningApproaches.length > 0 ? tcgaBundleRunningApproaches.join(", ") : "Background preprocessing"}
                  />
                  <KeyValue
                    label="Completed"
                    value={tcgaBundleCompletedApproaches.length > 0 ? tcgaBundleCompletedApproaches.join(", ") : "None yet"}
                  />
                </div>
              </div>
            </div>
          </div>
        </Panel>

        <Panel>
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <SectionTitle
              icon={<Layers3 className="h-5 w-5" />}
              title="Complex triad live runner"
              label={approach2Busy ? `running ${approach2Busy}` : hasRunningApproach2Experiment ? "live polling" : "mounted"}
            />
            <div className="grid gap-2 sm:grid-cols-2 lg:min-w-[760px] xl:grid-cols-6">
              <ActionButton
                busy={approach2Busy === "train"}
                disabled={Boolean(approach2Busy)}
                icon={<Play className="h-4 w-4" />}
                label="Run Approach 1"
                onClick={() => void runPresetTraining("Approach1")}
              />
              <ActionButton
                busy={approach2Busy === "train"}
                disabled={Boolean(approach2Busy)}
                icon={<Play className="h-4 w-4" />}
                label="Run Approach 2"
                onClick={() => void runPresetTraining("Approach2")}
              />
              <ActionButton
                busy={approach2Busy === "train"}
                disabled={Boolean(approach2Busy)}
                icon={<Dice5 className="h-4 w-4" />}
                label="Run Approach 3"
                onClick={() => void runPresetTraining("MonteCarlo")}
              />
              <ActionButton
                busy={approach2Busy === "triad"}
                disabled={Boolean(approach2Busy)}
                icon={<Layers3 className="h-4 w-4" />}
                label="Run Full Triad"
                onClick={() => runApproach2Action("triad")}
              />
              <ActionButton
                busy={approach2Busy === "tcga-triad"}
                disabled={Boolean(approach2Busy)}
                icon={<Database className="h-4 w-4" />}
                label="Run TCGA Adaptive"
                onClick={() => void runTcgaSlideTriad()}
              />
              <ActionButton
                busy={approach2Busy === "experiments"}
                disabled={Boolean(approach2Busy)}
                icon={<RefreshCw className="h-4 w-4" />}
                label="Refresh live"
                onClick={() => {
                  void runApproach2Action("experiments");
                  if (tcgaSlideBundleId) {
                    void fetchTcgaSlideTriadStatus(tcgaSlideBundleId, { silent: true });
                  }
                }}
              />
            </div>
          </div>

          <div className="mt-5 grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
            <div className="rounded-3xl border p-4" style={{ borderColor: "var(--card-border)", background: "var(--card-bg)" }}>
              <h3 className="font-semibold" style={{ color: "var(--heading)" }}>Live run inputs</h3>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <FormField
                  label="Approach label"
                  value={patchTrainingForm.approachLabel}
                  onChange={(value) =>
                    setPatchTrainingForm((current) => ({
                      ...current,
                      approachLabel: (value || "Approach2") as PatchTrainingForm["approachLabel"],
                    }))
                  }
                />
                <FormField
                  label="Experiment"
                  value={patchTrainingForm.experimentName}
                  onChange={(value) =>
                    setPatchTrainingForm((current) => ({
                      ...current,
                      experimentName: value,
                    }))
                  }
                />
                <FormField
                  label="Backbone"
                  value={patchTrainingForm.backbone}
                  onChange={(value) =>
                    setPatchTrainingForm((current) => ({
                      ...current,
                      backbone: value,
                    }))
                  }
                />
                <FormField
                  label="Dataset source"
                  value={patchTrainingForm.datasetSource}
                  onChange={(value) =>
                    setPatchTrainingForm((current) => ({
                      ...current,
                      datasetSource: (value || "workspace_root") as PatchTrainingForm["datasetSource"],
                    }))
                  }
                />
                {patchTrainingForm.datasetSource === "workspace_root" ? (
                  <FormField
                    label="Workspace root"
                    value={patchTrainingForm.workspaceRoot}
                    onChange={(value) =>
                      setPatchTrainingForm((current) => ({
                        ...current,
                        workspaceRoot: value,
                      }))
                    }
                    className="sm:col-span-2"
                  />
                ) : null}
                {patchTrainingForm.datasetSource !== "google_bucket" ? (
                  <FormField
                    label="Dataset path"
                    value={patchTrainingForm.datasetPath}
                    onChange={(value) =>
                      setPatchTrainingForm((current) => ({
                        ...current,
                        datasetPath: value,
                      }))
                    }
                    className="sm:col-span-2"
                  />
                ) : null}
                {patchTrainingForm.datasetSource === "google_bucket" ? (
                  <FormField
                    label="Google bucket"
                    value={patchTrainingForm.googleBucketUri}
                    onChange={(value) =>
                      setPatchTrainingForm((current) => ({
                        ...current,
                        googleBucketUri: value,
                      }))
                    }
                    className="sm:col-span-2"
                  />
                ) : null}
                <FormField
                  label="Epochs"
                  inputMode="numeric"
                  value={String(patchTrainingForm.epochs)}
                  onChange={(value) =>
                    setPatchTrainingForm((current) => ({
                      ...current,
                      epochs: Number(value) || 0,
                    }))
                  }
                />
                <FormField
                  label="Batch size"
                  inputMode="numeric"
                  value={String(patchTrainingForm.batchSize)}
                  onChange={(value) =>
                    setPatchTrainingForm((current) => ({
                      ...current,
                      batchSize: Number(value) || 0,
                    }))
                  }
                />
                <FormField
                  label="Learning rate"
                  value={String(patchTrainingForm.learningRate)}
                  onChange={(value) =>
                    setPatchTrainingForm((current) => ({
                      ...current,
                      learningRate: Number(value) || 0,
                    }))
                  }
                />
                <FormField
                  label="Validation split"
                  value={String(patchTrainingForm.valSplit)}
                  onChange={(value) =>
                    setPatchTrainingForm((current) => ({
                      ...current,
                      valSplit: Number(value) || 0,
                    }))
                  }
                />
                <FormField
                  label="Image size"
                  inputMode="numeric"
                  value={String(patchTrainingForm.imageSize)}
                  onChange={(value) =>
                    setPatchTrainingForm((current) => ({
                      ...current,
                      imageSize: Number(value) || 0,
                    }))
                  }
                />
                <FormField
                  label="Workers"
                  inputMode="numeric"
                  value={String(patchTrainingForm.numWorkers)}
                  onChange={(value) =>
                    setPatchTrainingForm((current) => ({
                      ...current,
                      numWorkers: Number(value) || 0,
                    }))
                  }
                />
              </div>
              <div className="mt-4 rounded-3xl border p-4 text-sm leading-6" style={{ borderColor: "var(--card-border)", background: "var(--btn-bg)", color: "var(--muted)" }}>
                <p>
                  Active dataset source: `{patchTrainingForm.datasetSource}` {"->"} `{patchDatasetSourceSummary(patchTrainingForm)}`.
                </p>
                <p className="mt-2">
                  `Run TCGA Adaptive` uses the VM bucket `gs://wsi_aiml_repo/TCGA/TCGA_COAD/TCGA_COAD`, matches it against `annotations/tcga_coad_bucket_annotations_pub.csv`, keeps an 18-slide balanced subset by default, uses 3-fold validation, and automatically shrinks slide count or folds if the matched cohort is smaller than requested.
                </p>
                {patchTrainingForm.datasetSource === "google_bucket" ? (
                  <p className="mt-2">
                    Paste a bucket URI like `gs://my-bucket/msi/CRC-VAL-HE-7K`, then use `Run selected preset`, `Run patch training`, or `Run full triad`. Bucket-backed patch runs are executed on the VM and staged into `datasets/staged_&lt;experiment_id&gt;` before training starts.
                  </p>
                ) : (
                  <p className="mt-2">
                    This runner defaults to the nine-folder CRC patch tree under `E:\4basecare-MSI\datasets\CRC-VAL-HE-7K`. Use `custom_path` if your patch dataset lives somewhere else on the local workstation.
                  </p>
                )}
              </div>
            </div>

            <div className="grid gap-4">
              <pre className="min-h-52 overflow-auto rounded-3xl border p-4 text-xs leading-5" style={{ borderColor: "var(--input-border)", background: "var(--input-bg)", color: approach2Error ? "var(--danger)" : "var(--input-text)" }}>
                {approach2Error || approach2Message}
              </pre>
              <div className="rounded-3xl border p-4" style={{ borderColor: "var(--card-border)", background: "var(--card-bg)" }}>
                <h3 className="font-semibold" style={{ color: "var(--heading)" }}>Predict uploaded patch</h3>
                <p className="mt-2 text-sm leading-6" style={{ color: "var(--muted)" }}>
                  Upload one `.tif`, `.png`, or `.jpg` patch and run inference with the latest completed model for the selected approach, or choose a specific experiment id below.
                </p>
                <label
                  className="mt-4 flex min-h-12 cursor-pointer items-center justify-between gap-3 rounded-full border border-dashed px-4 text-sm transition"
                  style={{ borderColor: "var(--accent-border)", background: "var(--btn-bg)" }}
                >
                  <span className="flex min-w-0 items-center gap-2" style={{ color: "var(--muted)" }}>
                    <Upload className="h-4 w-4 shrink-0" />
                    <span className="truncate">{predictionFile ? predictionFile.name : "No patch selected"}</span>
                  </span>
                  <span className="shrink-0 rounded-full px-3 py-1 font-semibold" style={{ background: "var(--accent-dim)", color: "var(--tag-text)" }}>
                    Choose
                  </span>
                  <input
                    accept=".tif,.tiff,.png,.jpg,.jpeg"
                    className="sr-only"
                    type="file"
                    onChange={(event) => setPredictionFile(event.target.files?.[0])}
                  />
                </label>
                <div className="mt-4 grid gap-3">
                  <FormField
                    label="Specific experiment id"
                    value={patchTrainingForm.selectedExperimentId}
                    onChange={(value) =>
                      setPatchTrainingForm((current) => ({
                        ...current,
                        selectedExperimentId: value,
                      }))
                    }
                  />
                  <ActionButton
                    busy={approach2Busy === "predict-upload"}
                    disabled={Boolean(approach2Busy) || !predictionFile}
                    icon={<Sigma className="h-4 w-4" />}
                    label="Predict uploaded patch"
                    onClick={() => runUploadedPrediction()}
                  />
                </div>
                {predictionResult ? (
                  <div className="mt-4 grid gap-2">
                    <KeyValue label="Experiment" value={predictionResult.experiment_id} />
                    <KeyValue label="Approach" value={predictionResult.approach_label} />
                    <KeyValue label="Prediction" value={predictionResult.prediction} />
                    <KeyValue label="Probability" value={readableMetric(predictionResult.probability) || "Pending"} />
                  </div>
                ) : null}
              </div>
            </div>
          </div>
        </Panel>

        <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_420px]">
        <Panel>
          <SectionTitle
            icon={<Database className="h-5 w-5" />}
            title="TCGA adaptive live bundle"
            label={tcgaBundleState || (tcgaSlideBundleId ? "queued" : "ready")}
          />
          <div className="mt-5 grid gap-3 sm:grid-cols-4">
            <MetricTile
              label="Matched"
              tone="blue"
              value={tcgaBundleMatchedSlides !== undefined ? String(tcgaBundleMatchedSlides) : "Pending"}
            />
            <MetricTile
              label="Selected"
              tone="teal"
              value={tcgaBundleSelectedSlides !== undefined ? String(tcgaBundleSelectedSlides) : "Pending"}
            />
            <MetricTile
              label="Downloaded"
              tone="coral"
              value={tcgaBundleDownloadedSlides !== undefined ? String(tcgaBundleDownloadedSlides) : "Pending"}
            />
            <MetricTile
              label="Extractor"
              tone="blue"
              value={tcgaBundleFeatureExtractor || "Pending"}
            />
          </div>
          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            <KeyValue label="Bundle ID" value={tcgaSlideBundleId || "Not started"} />
            <KeyValue label="State" value={tcgaBundleState || "idle"} />
            <KeyValue
              label="Labels"
              value={
                Object.keys(tcgaBundleLabelCounts).length > 0
                  ? Object.entries(tcgaBundleLabelCounts)
                      .map(([key, value]) => `${key} ${value}`)
                      .join(" | ")
                  : "Pending"
              }
            />
            <KeyValue
              label="Running"
              value={tcgaBundleRunningApproaches.length > 0 ? tcgaBundleRunningApproaches.join(", ") : "None"}
            />
            <KeyValue
              label="Completed"
              value={tcgaBundleCompletedApproaches.length > 0 ? tcgaBundleCompletedApproaches.join(", ") : "None"}
            />
            <KeyValue label="Remote status" value={tcgaSlideBundlePath || "Will appear after launch"} />
          </div>
          <div className="mt-5 grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
            <div className="rounded-3xl border p-4" style={{ borderColor: "var(--card-border)", background: "var(--card-bg)" }}>
              <h3 className="font-semibold" style={{ color: "var(--heading)" }}>Selected slides</h3>
              <div className="mt-3 max-h-64 overflow-auto rounded-3xl border p-3 text-sm leading-6" style={{ borderColor: "var(--border)", background: "var(--btn-bg)", color: "var(--body)" }}>
                {tcgaBundleSelectedNames.length > 0 ? (
                  tcgaBundleSelectedNames.map((slideName) => (
                    <div key={slideName} className="border-b py-2 last:border-b-0" style={{ borderColor: "var(--border)" }}>
                      {slideName}
                    </div>
                  ))
                ) : (
                  <p>No slide subset materialized yet. Launch `Run TCGA Adaptive` to build the bundle from the bucket and annotations.</p>
                )}
              </div>
            </div>
            <div className="rounded-3xl border p-4" style={{ borderColor: "var(--card-border)", background: "var(--card-bg)" }}>
              <h3 className="font-semibold" style={{ color: "var(--heading)" }}>Approach bundle output</h3>
              <div className="mt-3 grid gap-3">
                {(["Approach1", "Approach2", "MonteCarlo"] as const).map((label) => {
                  const payload = tcgaBundleApproachSummary[label] ?? {};
                  return (
                    <div key={label} className="rounded-3xl border p-3" style={{ borderColor: "var(--border)", background: "var(--btn-bg)" }}>
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-sm font-semibold" style={{ color: "var(--heading)" }}>{label}</span>
                        <span className="text-xs" style={{ color: "var(--muted)" }}>
                          {readableMetric(payload.mil_model) || "MIL"}
                        </span>
                      </div>
                      <div className="mt-2 grid gap-1 text-xs" style={{ color: "var(--body)" }}>
                        <span>AUROC: {readableMetric(payload.mean_auroc) || "Pending"}</span>
                        <span>Macro F1: {readableMetric(payload.mean_f1_macro) || "Pending"}</span>
                        <span>Folds: {readableMetric(payload.folds) || "Pending"}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </Panel>

        <Panel>
          <SectionTitle
            icon={<Activity className="h-5 w-5" />}
            title="Live experiment scores"
              label={`${approach2Experiments.length} runs`}
            />
            <div className="mt-5 grid gap-3 sm:grid-cols-4">
              <MetricTile
                label="Accuracy"
                tone="teal"
                value={readableMetric(latestApproach2Metrics?.best_val_accuracy) || "Pending"}
              />
              <MetricTile
                label="Macro F1"
                tone="blue"
                value={readableMetric(latestApproach2Metrics?.final_val_f1_macro) || "Pending"}
              />
              <MetricTile
                label="AUROC"
                tone="coral"
                value={readableMetric(latestApproach2Metrics?.val_auroc_ovr_macro) || "Pending"}
              />
              <MetricTile
                label="Epochs"
                tone="blue"
                value={latestApproach2History.length > 0 ? String(latestApproach2History.length) : "Pending"}
              />
            </div>
            <div className="mt-4 grid gap-2 sm:grid-cols-2">
              <KeyValue label="Approach counts" value={`A1 ${approachExperimentCounts.Approach1 ?? 0} | A2 ${approachExperimentCounts.Approach2 ?? 0} | A3 ${approachExperimentCounts.MonteCarlo ?? 0}`} />
              <KeyValue label="Latest run" value={latestApproach2Experiment?.name ?? "No run yet"} />
              <KeyValue label="Status" value={latestApproach2Experiment?.status ?? "idle"} />
              <KeyValue label="Backbone" value={readableMetric(latestApproach2Metrics?.backbone) || "Pending"} />
              <KeyValue label="Train / val images" value={latestApproach2Metrics ? `${readableMetric(latestApproach2Metrics.train_images)} / ${readableMetric(latestApproach2Metrics.val_images)}` : "Pending"} />
            </div>
            <div className="mt-5 max-h-96 overflow-auto rounded-3xl border" style={{ borderColor: "var(--card-border)", background: "var(--card-bg)" }}>
              {approach2Experiments.length > 0 ? (
                approach2Experiments.map((experiment) => (
                  <div className="grid gap-2 border-b p-4 last:border-b-0 sm:grid-cols-6" style={{ borderColor: "var(--border)" }} key={experiment.experiment_id}>
                    <span className="font-mono text-xs" style={{ color: "var(--teal)" }}>{experiment.experiment_id}</span>
                    <span className="text-sm font-semibold" style={{ color: "var(--heading)" }}>{experiment.name}</span>
                    <span className="text-sm" style={{ color: "var(--body)" }}>{experimentApproachLabel(experiment)}</span>
                    <span className="text-sm" style={{ color: experiment.status === "completed" ? "var(--teal)" : "var(--warning)" }}>{experiment.status}</span>
                    <span className="text-sm" style={{ color: "var(--body)" }}>{readableMetric(experiment.metrics?.best_val_accuracy) || "pending"}</span>
                    <span className="text-sm" style={{ color: "var(--muted)" }}>{Array.isArray(experiment.metrics?.history) ? `${experiment.metrics.history.length} epochs` : "epochs pending"}</span>
                  </div>
                ))
              ) : (
                <p className="p-4 text-sm leading-6" style={{ color: "var(--muted)" }}>
                  Run one preset or the full triad to create CRC comparison experiments, then this panel will auto-refresh while the VM bundle is training.
                </p>
              )}
            </div>
          </Panel>

          <Panel>
            <SectionTitle
              icon={<Dice5 className="h-5 w-5" />}
              title="Epoch history"
              label={latestApproach2History.length > 0 ? `${latestApproach2History.length} rows` : "waiting"}
            />
            <div className="mt-4 max-h-96 overflow-auto rounded-3xl border" style={{ borderColor: "var(--card-border)", background: "var(--card-bg)" }}>
              {latestApproach2History.length > 0 ? (
                <table className="w-full text-left text-xs">
                  <thead className="sticky top-0 backdrop-blur" style={{ background: "var(--panel-bg)" }}>
                    <tr>
                      <th className="px-3 py-2 font-semibold" style={{ color: "var(--muted)" }}>Epoch</th>
                      <th className="px-3 py-2 font-semibold" style={{ color: "var(--muted)" }}>Train loss</th>
                      <th className="px-3 py-2 font-semibold" style={{ color: "var(--muted)" }}>Val loss</th>
                      <th className="px-3 py-2 font-semibold" style={{ color: "var(--muted)" }}>Accuracy</th>
                      <th className="px-3 py-2 font-semibold" style={{ color: "var(--muted)" }}>Macro F1</th>
                    </tr>
                  </thead>
                  <tbody>
                    {latestApproach2History.map((entry, index) => (
                      <tr key={`${index}-${readableMetric(entry.epoch)}`} className="border-t" style={{ borderColor: "var(--border)" }}>
                        <td className="px-3 py-2" style={{ color: "var(--heading)" }}>{readableMetric(entry.epoch)}</td>
                        <td className="px-3 py-2 font-mono" style={{ color: "var(--body)" }}>{readableMetric(entry.train_loss)}</td>
                        <td className="px-3 py-2 font-mono" style={{ color: "var(--body)" }}>{readableMetric(entry.val_loss)}</td>
                        <td className="px-3 py-2 font-mono" style={{ color: "var(--teal)" }}>{readableMetric(entry.val_accuracy)}</td>
                        <td className="px-3 py-2 font-mono" style={{ color: "var(--blue)" }}>{readableMetric(entry.val_f1_macro)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="p-4 text-sm leading-6" style={{ color: "var(--muted)" }}>
                  When a run finishes, epoch-wise loss, accuracy, and F1 will show here.
                </p>
              )}
            </div>
            <div className="mt-4 grid gap-2">
              <KeyValue label="Dataset" value={readableMetric(latestApproach2Metrics?.dataset_path) || patchTrainingForm.datasetPath} />
              <KeyValue label="Classes" value={Array.isArray(latestApproach2Metrics?.class_names) ? latestApproach2Metrics.class_names.join(", ") : "ADI, BACK, DEB, LYM, MUC, MUS, NORM, STR, TUM"} />
              <KeyValue label="Model artifact" value={readableMetric((latestApproach2Metrics?.artifacts as Record<string, unknown> | undefined)?.model_path) || "Pending"} />
            </div>
          </Panel>
        </section>

        <Panel>
          <SectionTitle
            icon={<BarChart3 className="h-5 w-5" />}
            title="Approach 2 advanced charts"
            label={approach2Analytics?.completed_runs ? `${approach2Analytics.completed_runs} completed` : "waiting"}
          />
          <div className="mt-5">
            <Approach2AdvancedCharts
              history={
                (approach2Analytics?.history as Array<{
                  epoch?: number;
                  train_loss?: number;
                  val_loss?: number;
                  val_accuracy?: number;
                  val_f1_macro?: number;
                }>) ?? []
              }
              classDistribution={approach2Analytics?.class_distribution ?? {}}
            />
          </div>
        </Panel>
      </section>

      <section className={`relative z-10 mx-auto w-full max-w-[1500px] gap-5 px-4 pb-10 sm:px-6 lg:px-8 ${approachMode === "monte-carlo" ? "grid" : "hidden"}`}>
        <Panel>
          <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
            <SectionTitle
              icon={<Dice5 className="h-5 w-5" />}
              title="Monte Carlo approach"
              label={mcPlan ? `${mcPlan.trial_count} trials` : "stochastic validation"}
            />
            <div className="grid gap-2 sm:grid-cols-2 xl:min-w-[720px] xl:grid-cols-5">
              <ActionButton
                busy={mcBusy === "vm-workspace"}
                disabled={Boolean(mcBusy)}
                icon={<Server className="h-4 w-4" />}
                label="Prep VM cache"
                onClick={() => prepareMCVmWorkspace()}
              />
              <ActionButton
                busy={mcBusy === "plan"}
                disabled={Boolean(mcBusy)}
                icon={<Dice5 className="h-4 w-4" />}
                label="Generate plan"
                onClick={() => generateMCPlan()}
              />
              <ActionButton
                busy={mcBusy === "bootstrap-runners"}
                disabled={Boolean(mcBusy)}
                icon={<Upload className="h-4 w-4" />}
                label="Bootstrap"
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
                label="Uncertainty"
                onClick={() => {
                  const tid = bestExperiment?.best?.trial_id;
                  if (tid) {
                    void fetchMCDropout(tid);
                    void fetchBootstrapCI(tid);
                  }
                }}
              />
            </div>
          </div>

          {mcError ? (
            <p className="mt-4 rounded-2xl border p-3 text-sm leading-6" style={{ borderColor: "rgba(217,93,72,0.3)", background: "rgba(217,93,72,0.1)", color: "var(--danger-deep)" }}>
              {mcError}
            </p>
          ) : null}

          <div className="mt-5 grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
            <div className="rounded-3xl border p-4" style={{ borderColor: "var(--card-border)", background: "var(--card-bg)" }}>
              <h3 className="font-semibold" style={{ color: "var(--heading)" }}>VM and model storage</h3>
              <p className="mt-2 text-sm leading-6" style={{ color: "var(--body)" }}>
                The VM prep action creates `models/huggingface_cache`, `models/monte_carlo`, and an AI integration env template inside the remote project.
              </p>
              <pre className="mt-4 max-h-72 overflow-auto rounded-3xl border p-4 text-xs leading-5" style={{ borderColor: "var(--input-border)", background: "var(--input-bg)", color: "var(--input-text)" }}>
                {mcVmPrep || "Click Prep VM cache to create the Monte Carlo and Hugging Face model folders on the VM."}
              </pre>
            </div>

            <div className="rounded-3xl border p-4" style={{ borderColor: "var(--card-border)", background: "var(--card-bg)" }}>
              <h3 className="font-semibold" style={{ color: "var(--heading)" }}>AI providers</h3>
              <div className="mt-4 grid gap-2">
                {integrations.map((integration) => (
                  <KeyValue
                    key={integration.name}
                    label={integration.name}
                    value={integration.configured ? "configured" : integration.env_var}
                  />
                ))}
              </div>
            </div>
          </div>
        </Panel>

        <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_420px]">
          <Panel>
            <SectionTitle
              icon={<BarChart3 className="h-5 w-5" />}
              title="Random trial plan"
              label={mcPlan ? `seed ${mcPlan.random_seed}` : "not generated"}
            />
            <div className="mt-5 max-h-96 overflow-auto rounded-3xl border" style={{ borderColor: "var(--card-border)", background: "var(--card-bg)" }}>
              {mcPlan ? (
                <table className="w-full text-left text-xs">
                  <thead className="sticky top-0 backdrop-blur" style={{ background: "var(--panel-bg)" }}>
                    <tr>
                      <th className="px-3 py-2 font-semibold" style={{ color: "var(--muted)" }}>Trial</th>
                      <th className="px-3 py-2 font-semibold" style={{ color: "var(--muted)" }}>Model</th>
                      <th className="px-3 py-2 font-semibold" style={{ color: "var(--muted)" }}>Extractor</th>
                      <th className="px-3 py-2 font-semibold" style={{ color: "var(--muted)" }}>LR</th>
                      <th className="px-3 py-2 font-semibold" style={{ color: "var(--muted)" }}>Epochs</th>
                    </tr>
                  </thead>
                  <tbody>
                    {mcPlan.trials.map((trial) => (
                      <tr key={trial.trial_id} className="border-t" style={{ borderColor: "var(--border)" }}>
                        <td className="px-3 py-2 font-mono" style={{ color: "var(--teal)" }}>{trial.trial_id.slice(0, 13)}</td>
                        <td className="px-3 py-2" style={{ color: "var(--heading)" }}>{trial.mil_model}</td>
                        <td className="px-3 py-2" style={{ color: "var(--body)" }}>{trial.feature_extractor}</td>
                        <td className="px-3 py-2 font-mono" style={{ color: "var(--blue)" }}>{trial.learning_rate.toExponential(2)}</td>
                        <td className="px-3 py-2" style={{ color: "var(--muted)" }}>{trial.epochs}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="p-4 text-sm leading-6" style={{ color: "var(--muted)" }}>
                  Generate a plan to sample model, extractor, learning rate, dropout, weight decay, epoch, and seed combinations.
                </p>
              )}
            </div>
          </Panel>

          <Panel>
            <SectionTitle
              icon={<Shield className="h-5 w-5" />}
              title="Stable ranking"
              label={mcStableBest ? `${mcStableBest.total_evaluated} evaluated` : "pending"}
            />
            <div className="mt-5 grid gap-2">
              {mcStableBest?.best ? (
                <>
                  <KeyValue label="Trial" value={mcStableBest.best.trial_id} />
                  <KeyValue label="Score" value={mcStableBest.best.stability_score.toFixed(4)} />
                  <KeyValue label="Mean AUROC" value={mcStableBest.best.mean_auroc.toFixed(4)} />
                  <KeyValue label="SD AUROC" value={mcStableBest.best.sd_auroc.toFixed(4)} />
                </>
              ) : (
                <p className="text-sm leading-6" style={{ color: "var(--muted)" }}>
                  Run Stable best after completed VM metrics exist.
                </p>
              )}
            </div>
          </Panel>
        </section>

        <Panel>
          <SectionTitle
            icon={<BarChart3 className="h-5 w-5" />}
            title="Monte Carlo analytics"
            label={monteCarloAnalytics?.total_candidates ? `${monteCarloAnalytics.total_candidates} candidates` : "stochastic view"}
          />
          <div className="mt-5">
            <MonteCarloAdvancedCharts
              plan={mcPlan}
              stableBest={mcStableBest}
              summary={{
                mc_result_trials: monteCarloAnalytics?.mc_result_trials ?? 0,
                dropout_ready: monteCarloAnalytics?.dropout_ready ?? 0,
                bootstrap_ready: monteCarloAnalytics?.bootstrap_ready ?? 0,
                total_candidates: monteCarloAnalytics?.total_candidates ?? 0,
              }}
            />
          </div>
        </Panel>
      </section>

      <section className={`relative z-10 mx-auto w-full max-w-[1500px] gap-5 px-4 pb-10 sm:px-6 lg:px-8 ${approachMode === "parallel" ? "grid" : "hidden"}`}>
        <Panel>
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <SectionTitle
              icon={<Layers3 className="h-5 w-5" />}
              title="Parallel Metrics Snapshot"
              label={parallelBusy ? "running" : "ready"}
            />
            <div className="grid gap-2 sm:grid-cols-2 lg:min-w-[420px] xl:grid-cols-2">
              <ActionButton
                busy={parallelBusy}
                disabled={parallelBusy}
                icon={<Play className="h-4 w-4" />}
                label="Fetch Metrics Snapshot"
                onClick={() => runParallelPipeline()}
              />
            </div>
          </div>
          <div className="mt-5">
             <pre className="min-h-[60px] overflow-auto rounded-3xl border p-4 text-xs leading-5" style={{ borderColor: "var(--input-border)", background: "var(--input-bg)", color: parallelError ? "var(--danger)" : "var(--input-text)" }}>
                {parallelError || parallelMessage}
             </pre>
          </div>

          <div className="mt-5 grid gap-3 sm:grid-cols-3">
            {parallelSources.length > 0 ? (
              parallelSources.map((source) => (
                <div
                  key={source.name}
                  className="rounded-3xl border p-4"
                  style={{ borderColor: "var(--card-border)", background: "var(--card-bg)" }}
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-semibold" style={{ color: "var(--heading)" }}>
                      {source.name}
                    </p>
                    <span
                      className="rounded-full px-2 py-1 text-xs font-semibold"
                      style={{
                        background: source.ok ? "var(--accent-dim)" : "rgba(217,93,72,0.12)",
                        color: source.ok ? "var(--teal)" : "var(--coral)",
                      }}
                    >
                      {source.ok ? "available" : "error"}
                    </span>
                  </div>
                  <p className="mt-3 text-2xl font-semibold" style={{ color: "var(--blue)" }}>
                    {source.records_found}
                  </p>
                  <p className="mt-1 text-xs leading-5" style={{ color: "var(--muted)" }}>
                    {source.records_found > 0
                      ? `${source.records_found} real result artifact(s) found.`
                      : source.message || "No completed result artifact found yet."}
                  </p>
                </div>
              ))
            ) : (
              <p className="text-sm leading-6" style={{ color: "var(--muted)" }}>
                Source availability will appear here after the metrics snapshot completes.
              </p>
            )}
          </div>
          
          <div className="mt-8">
             <SectionTitle
               icon={<BarChart3 className="h-5 w-5" />}
               title="Parallel Results Visualization"
               label={parallelMetrics.length > 0 ? "rendered" : "waiting"}
             />
             {parallelMetrics.length > 0 ? (
               <div className="mt-5">
                 <ParallelResults data={parallelMetrics} />
               </div>
             ) : (
               <p className="mt-4 text-sm leading-6" style={{ color: "var(--muted)" }}>
                 Run the snapshot after completed VM or platform metrics exist. The chart stays empty until real artifacts are found.
               </p>
             )}
          </div>
        </Panel>
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
        borderColor: isDark ? "rgba(226,232,240,0.22)" : "rgba(255,255,255,0.7)",
        background: isDark ? "rgba(226,232,240,0.09)" : "rgba(255,255,255,0.45)",
        color: isDark ? "#c6ccd5" : "#36575a",
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

function formatEpochTime(epochSeconds: number) {
  if (!Number.isFinite(epochSeconds)) {
    return "";
  }
  return new Date(epochSeconds * 1000).toLocaleTimeString();
}

function formatBytes(bytes: number) {
  if (!Number.isFinite(bytes) || bytes <= 0) {
    return "0 B";
  }
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let index = 0;
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024;
    index += 1;
  }
  return `${value.toFixed(value >= 10 || index === 0 ? 0 : 1)} ${units[index]}`;
}

function tcgaStageMeta(
  state: string,
  downloadedSlides?: number,
  selectedSlides?: number,
  completedApproaches = 0,
  tfrecordFiles?: number,
) {
  const safeSelected = Math.max(selectedSlides ?? 0, 0);
  const safeDownloaded = Math.max(downloadedSlides ?? 0, 0);
  const downloadProgress = safeSelected > 0 ? Math.min(safeDownloaded / safeSelected, 1) : 0;
  const trainingProgress = Math.min(completedApproaches / 3, 1);
  const extractionProgress = safeSelected > 0 ? Math.min((tfrecordFiles ?? 0) / safeSelected, 1) : 0;

  switch (state) {
    case "matching_annotations":
      return {
        percent: 10,
        label: "matching",
        title: "Matching annotations against bucket slides",
        detail: "The VM is lining up the TCGA bucket files with the MSI annotation table before any slide download starts.",
      };
    case "downloading_slides":
      return {
        percent: Math.round(18 + downloadProgress * 24),
        label: "downloading",
        title: "Downloading selected SVS slides in the background",
        detail: "This run is active on the VM and pulling the chosen whole-slide images into the triad bundle workspace.",
      };
    case "extracting_tiles":
      return {
        percent: Math.max(42, Math.round(42 + extractionProgress * 22)),
        label: "tiling",
        title: "Extracting pathology tiles from the downloaded slides",
        detail: `The VM is preprocessing the selected slides with Slideflow and cucim. TFRecords ready: ${tfrecordFiles ?? 0}/${safeSelected || "?"}. This stage can take the longest before GPU-heavy feature generation starts.`,
      };
    case "retrying_tiles":
      return {
        percent: 58,
        label: "retrying",
        title: "Retrying tile extraction with lighter settings",
        detail: "The stricter QC path came up empty, so the runner is retrying extraction with a more permissive fallback instead of stopping the bundle.",
      };
    case "generating_features":
      return {
        percent: 70,
        label: "features",
        title: "Generating pathology feature bags",
        detail: "The selected feature extractor is building slide-level bags that the MIL approaches will train on next.",
      };
    case "prepared":
      return {
        percent: 78,
        label: "prepared",
        title: "Bundle prepared and ready to train",
        detail: "Slides, tiles, and feature bags are ready. The VM is about to fan out the three MIL approaches in parallel.",
      };
    case "training_parallel":
      return {
        percent: Math.round(80 + trainingProgress * 18),
        label: "training",
        title: "Training all MIL approaches in parallel",
        detail: "The background runner is now executing Approach 1, Approach 2, and Monte Carlo variants in parallel on the prepared bundle.",
      };
    case "completed":
      return {
        percent: 100,
        label: "completed",
        title: "Bundle completed",
        detail: "The TCGA adaptive bundle has finished and the per-approach metrics are available below.",
      };
    case "failed":
      return {
        percent: 100,
        label: "failed",
        title: "Bundle failed",
        detail: "The background runner stopped with an error. The bundle card below and the remote status path contain the failure details.",
      };
    default:
      return {
        percent: 4,
        label: state || "ready",
        title: "Ready to launch the next TCGA adaptive run",
        detail: "No active background bundle is being tracked yet. Launch a run or refresh the latest saved bundle id.",
      };
  }
}

function tcgaStageChart(state: string) {
  const stages = [
    {
      key: "matching_annotations",
      short: "Match",
      title: "Annotation match",
    },
    {
      key: "downloading_slides",
      short: "Download",
      title: "Slide download",
    },
    {
      key: "extracting_tiles",
      short: "Tiles",
      title: "Tile extraction",
    },
    {
      key: "generating_features",
      short: "Features",
      title: "Feature bags",
    },
    {
      key: "training_parallel",
      short: "Train",
      title: "Parallel MIL training",
    },
    {
      key: "completed",
      short: "Done",
      title: "Completed",
    },
  ] as const;

  const normalizedState =
    state === "retrying_tiles"
      ? "extracting_tiles"
      : state === "prepared"
        ? "training_parallel"
        : state;
  const currentIndex = stages.findIndex((stage) => stage.key === normalizedState);

  return stages.map((stage, index) => {
    const isCurrent = currentIndex === index;
    const isDone =
      currentIndex > index ||
      normalizedState === "completed" ||
      (normalizedState === "failed" && index < stages.length - 1);
    const isPending = !isCurrent && !isDone;
    return {
      ...stage,
      isCurrent,
      isDone,
      isPending,
    };
  });
}

function readableMetric(value: unknown) {
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number") {
    if (Number.isInteger(value)) {
      return value.toLocaleString();
    }
    return value.toFixed(4);
  }
  return "";
}

function numericMetric(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function readStringArray(value: unknown) {
  return Array.isArray(value) ? value.map((item) => String(item)) : [];
}

function experimentApproachLabel(experiment: Approach2Experiment) {
  const metricLabel = experiment.metrics?.approach_label;
  if (typeof metricLabel === "string" && metricLabel.length > 0) {
    return metricLabel;
  }
  const parameterLabel = experiment.parameters?.approach_label;
  if (typeof parameterLabel === "string" && parameterLabel.length > 0) {
    return parameterLabel;
  }
  return "Approach2";
}

function FormField({
  label,
  value,
  onChange,
  inputMode,
  className,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  inputMode?: React.HTMLAttributes<HTMLInputElement>["inputMode"];
  className?: string;
}) {
  return (
    <label className={`grid gap-2 ${className ?? ""}`}>
      <span className="text-sm font-medium" style={{ color: "var(--muted)" }}>
        {label}
      </span>
      <input
        className="min-h-11 rounded-2xl border px-3 text-sm outline-none"
        style={{
          borderColor: "var(--input-border)",
          background: "var(--input-bg)",
          color: "var(--input-text)",
        }}
        inputMode={inputMode}
        onChange={(event) => onChange(event.target.value)}
        type="text"
        value={value}
      />
    </label>
  );
}

