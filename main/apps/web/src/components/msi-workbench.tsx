"use client";

import Image from "next/image";
import { useEffect, useState, type ReactNode } from "react";
import { max as d3Max, scaleLinear } from "d3";
import {
  Activity,
  BarChart3,
  Database,
  HardDrive,
  RefreshCw,
  Server,
  TimerReset,
  TrendingUp,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const automationApiBase =
  process.env.NEXT_PUBLIC_MSI_API_URL ?? "http://127.0.0.1:8001";
const refreshSeconds = 30;
const bundleStorageKey = "msi-single-system-latest-bundle";

const tcgaDefaults = {
  experiment_name: "tcga-coad-dx1-single-system",
  bucket_uri: "gs://wsi_aiml_repo/TCGA/TCGA_COAD/TCGA_COAD",
  slide_limit: 110,
  n_folds: 2,
  preferred_slide_pattern: "DX",
  preferred_exact_suffix: "DX1",
  annotations_csv: "annotations/tcga_coad_bucket_annotations_final_all3_live_dx1.csv",
  feature_extractor: "ctranspath",
  tile_px: 256,
  tile_um: 128,
  max_parallel_approaches: 2,
} as const;

type BundleEnvelope = {
  bundle_id?: string;
  remote_status_path?: string;
  status?: Record<string, unknown>;
};

type ArchiveEnvelope = {
  archive_root?: string;
  summary?: Record<string, unknown>;
};

type HealthEnvelope = {
  ok?: string;
  service?: string;
  environment?: string;
};

type ApproachMetric = {
  mean_auroc?: number | null;
  mean_f1_macro?: number | null;
  mean_f1_macro_default_threshold?: number | null;
  mil_model?: string | null;
  epochs?: number | null;
  mean_epochs?: number | null;
  completed_batches?: number | null;
};

type BestBatchMetric = ApproachMetric & {
  bundle_id?: string;
};

type BatchSummary = {
  bundle_id?: string;
  slide_count?: number;
  feature_extractor_used?: string;
  label_counts?: Record<string, number>;
  approaches?: Record<string, ApproachMetric>;
};

export function MsiWorkbench() {
  const [health, setHealth] = useState<HealthEnvelope | null>(null);
  const [bundle, setBundle] = useState<BundleEnvelope | null>(null);
  const [archive, setArchive] = useState<ArchiveEnvelope | null>(null);
  const [bundleId, setBundleId] = useState("");
  const [busy, setBusy] = useState<"run" | "refresh" | null>(null);
  const [message, setMessage] = useState("Single TCGA DX1 system is ready.");
  const [error, setError] = useState("");
  const [refreshIn, setRefreshIn] = useState(refreshSeconds);

  useEffect(() => {
    document.documentElement.classList.add("snow-theme");
    return () => {
      document.documentElement.classList.remove("snow-theme");
    };
  }, []);

  useEffect(() => {
    const savedBundleId =
      typeof window !== "undefined"
        ? window.localStorage.getItem(bundleStorageKey) ?? ""
        : "";
    if (savedBundleId) {
      setBundleId(savedBundleId);
    }
    void refreshAll(savedBundleId);
  }, []);

  useEffect(() => {
    const interval = window.setInterval(() => {
      setRefreshIn((current) => (current <= 1 ? refreshSeconds : current - 1));
    }, 1000);
    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    const interval = window.setInterval(() => {
      void refreshAll(bundleId);
    }, refreshSeconds * 1000);
    return () => window.clearInterval(interval);
  }, [bundleId]);

  async function refreshAll(preferredBundleId?: string) {
    setBusy("refresh");
    setError("");
    try {
      const [healthRes, latestBundleRes, archiveRes] = await Promise.all([
        fetch(`${automationApiBase}/health`, { cache: "no-store" }),
        fetch(
          `${automationApiBase}/approach-2/pipeline/train-tcga-slide-triad-latest`,
          { cache: "no-store" },
        ),
        fetch(
          `${automationApiBase}/approach-2/pipeline/tcga-batch-archive-latest`,
          { cache: "no-store" },
        ),
      ]);

      const healthPayload = (await healthRes.json()) as HealthEnvelope;
      const latestBundlePayload = (await latestBundleRes.json()) as BundleEnvelope;
      const archivePayload = (await archiveRes.json()) as ArchiveEnvelope;

      setHealth(healthPayload);
      setArchive(archivePayload);

      const latestBundleId = String(latestBundlePayload.bundle_id ?? "");
      if (latestBundleId) {
        setBundleId(latestBundleId);
        if (typeof window !== "undefined") {
          window.localStorage.setItem(bundleStorageKey, latestBundleId);
        }
      }
      setBundle(latestBundlePayload);

      const archiveState = String(archivePayload.summary?.state ?? "");
      const bundleState = String(latestBundlePayload.status?.state ?? "");
      const sourceNote =
        preferredBundleId && latestBundleId && preferredBundleId !== latestBundleId
          ? ` Switched from stale bundle ${preferredBundleId} to ${latestBundleId}.`
          : "";
      setMessage(
        `Python API ${healthPayload.service ?? "service"} is ${healthPayload.ok === "true" ? "healthy" : "responding"}. Latest bundle: ${bundleState || "waiting"}. Latest archive: ${archiveState || "waiting"}.${sourceNote}`,
      );
      setRefreshIn(refreshSeconds);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to refresh the TCGA single system dashboard.",
      );
    } finally {
      setBusy(null);
    }
  }

  async function runDx1System() {
    setBusy("run");
    setError("");
    try {
      const response = await fetch(
        `${automationApiBase}/approach-2/pipeline/train-tcga-slide-triad`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(tcgaDefaults),
        },
      );
      const payload = (await response.json()) as BundleEnvelope & {
        message?: string;
      };
      if (!response.ok) {
        throw new Error(
          String(
            (payload as { detail?: string }).detail ??
              payload.message ??
              "Unable to launch the TCGA DX1 system run.",
          ),
        );
      }
      const nextBundleId = String(payload.bundle_id ?? "");
      if (nextBundleId) {
        setBundleId(nextBundleId);
        if (typeof window !== "undefined") {
          window.localStorage.setItem(bundleStorageKey, nextBundleId);
        }
      }
      setMessage(
        `${payload.message ?? "TCGA DX1 system queued."} Bundle ${nextBundleId} is now being tracked.`,
      );
      await refreshAll(nextBundleId);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to launch the TCGA DX1 system run.",
      );
    } finally {
      setBusy(null);
    }
  }

  const bundleStatus = bundle?.status ?? {};
  const bundleState = String(bundleStatus.state ?? "");
  const liveLabels = readLabelCounts(bundleStatus.label_counts);
  const archiveLabels = readLabelCounts(archive?.summary?.aggregate_label_counts);
  const labelCounts =
    Object.keys(liveLabels).length > 0 ? liveLabels : archiveLabels;
  const stage = tcgaStageMeta(
    bundleState,
    numericMetric(bundleStatus.downloaded_slide_count),
    numericMetric(bundleStatus.selected_slide_count),
    numericMetric(bundleStatus.tfrecord_files),
    completedApproachCount(bundleStatus.completed_approaches),
  );

  const archiveApproaches = readApproaches(archive?.summary?.aggregate_approaches);
  const liveApproaches = readApproaches(
    (bundleStatus.summary as { approaches?: Record<string, unknown> } | undefined)
      ?.approaches,
  );
  const approachMetrics =
    Object.keys(liveApproaches).length > 0 ? liveApproaches : archiveApproaches;

  const approachChartData = ["Approach1", "Approach2"]
    .map((label) => {
      const payload = approachMetrics[label];
      if (!payload) {
        return null;
      }
      return {
        label,
        auroc: payload.mean_auroc ?? 0,
        macroF1: payload.mean_f1_macro ?? 0,
        defaultF1: payload.mean_f1_macro_default_threshold ?? 0,
      };
    })
    .filter((item): item is { label: string; auroc: number; macroF1: number; defaultF1: number } => item !== null);

  const selectedSlides = readStringArray(bundleStatus.selected_slides);
  const bestBatches = readBestBatches(archive?.summary?.best_batch_by_auroc);
  const batches = readBatches(archive?.summary?.batches);

  return (
    <div className="snow-theme min-h-screen" style={{ background: "linear-gradient(180deg, #eef8ff 0%, #e7f4ff 44%, #f6fbff 100%)" }}>
      <main className="mx-auto flex w-full max-w-[1480px] flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
        <section
          className="overflow-hidden rounded-[34px] border p-6 shadow-[0_30px_90px_rgba(90,153,194,0.16)]"
          style={{
            borderColor: "var(--panel-border)",
            background:
              "radial-gradient(circle at top right, rgba(102,181,255,0.16), transparent 34%), linear-gradient(135deg, rgba(255,255,255,0.88), rgba(243,250,255,0.86))",
          }}
        >
          <div className="flex flex-col gap-6 xl:flex-row xl:items-start xl:justify-between">
            <div className="max-w-3xl">
              <span
                className="inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.22em]"
                style={{
                  borderColor: "rgba(102,181,255,0.28)",
                  background: "rgba(102,181,255,0.12)",
                  color: "#1f74b3",
                }}
              >
                Single System
              </span>
              <h1 className="mt-4 text-4xl font-semibold tracking-[-0.04em] sm:text-5xl" style={{ color: "var(--heading)" }}>
                TCGA DX1 MSI Runner
              </h1>
              <p className="mt-4 max-w-3xl text-base leading-7 sm:text-lg" style={{ color: "var(--body)" }}>
                One focused system only: Next.js for the live surface, Python for orchestration, GCS for slide sourcing, and DX1-only TCGA MSI training with advanced D3 and Recharts result views.
              </p>
              <div className="mt-5 flex flex-wrap gap-3">
                <ActionChip icon={<Server className="h-4 w-4" />} label={`API ${health?.ok === "true" ? "healthy" : "checking"}`} />
                <ActionChip icon={<Database className="h-4 w-4" />} label="DX1 TCGA lane" />
                <ActionChip icon={<BarChart3 className="h-4 w-4" />} label="D3 + Recharts visuals" />
                <ActionChip icon={<HardDrive className="h-4 w-4" />} label="VM-backed orchestration" />
              </div>
            </div>
            <div className="rounded-[30px] border p-4 sm:p-5" style={{ borderColor: "var(--card-border)", background: "rgba(255,255,255,0.72)" }}>
              <Image
                src="/assets/4basecare-mars.png"
                alt="4basecare MSI"
                width={260}
                height={160}
                className="h-auto w-[220px] sm:w-[260px]"
                priority
              />
            </div>
          </div>
        </section>

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            icon={<Activity className="h-5 w-5" />}
            label="Bundle state"
            value={stage.label}
            detail={stage.title}
          />
          <MetricCard
            icon={<TimerReset className="h-5 w-5" />}
            label="Estimated time left"
            value={stage.eta}
            detail={bundleId ? `${refreshIn}s to next refresh` : "Waiting for a tracked bundle"}
          />
          <MetricCard
            icon={<Database className="h-5 w-5" />}
            label="Latest archive"
            value={String(archive?.summary?.results_count ?? "Pending")}
            detail={String(archive?.summary?.state ?? "No archived batches yet")}
          />
          <MetricCard
            icon={<TrendingUp className="h-5 w-5" />}
            label="Feature extractor"
            value={
              String(bundleStatus.feature_extractor_used ?? "")
                || String(readStringArray(archive?.summary?.feature_extractors).join(", ") || "Pending")
            }
            detail="Current runner is locked to pathology-first defaults"
          />
        </section>

        <section className="grid gap-5 xl:grid-cols-[minmax(0,1.15fr)_minmax(360px,0.85fr)]">
          <Panel>
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <SectionTitle
                icon={<Activity className="h-5 w-5" />}
                title="Live TCGA runner"
                label={stage.label}
              />
              <div className="grid gap-2 sm:grid-cols-2">
                <ActionButton
                  busy={busy === "run"}
                  icon={<Database className="h-4 w-4" />}
                  label="Run DX1 system"
                  onClick={() => void runDx1System()}
                />
                <ActionButton
                  busy={busy === "refresh"}
                  icon={<RefreshCw className="h-4 w-4" />}
                  label="Refresh data"
                  onClick={() => void refreshAll(bundleId)}
                />
              </div>
            </div>
            <div className="mt-5 overflow-hidden rounded-[28px] border" style={{ borderColor: "var(--card-border)", background: "rgba(255,255,255,0.78)" }}>
              <div className="h-3 w-full" style={{ background: "rgba(70,102,217,0.12)" }}>
                <div
                  className="h-full rounded-r-full transition-all duration-500"
                  style={{
                    width: `${stage.percent}%`,
                    background:
                      bundleState === "failed"
                        ? "linear-gradient(90deg, rgba(217,93,72,0.92), rgba(217,93,72,0.58))"
                        : "linear-gradient(90deg, rgba(60,166,230,0.96), rgba(70,102,217,0.9))",
                  }}
                />
              </div>
              <div className="grid gap-5 p-5 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
                <div>
                  <div className="flex flex-wrap items-center gap-3">
                    <ActionChip label={`${stage.percent}% complete`} />
                    <ActionChip label={`ETA ${stage.eta}`} />
                    <ActionChip label={`Refresh ${refreshIn}s`} />
                  </div>
                  <h2 className="mt-4 text-xl font-semibold" style={{ color: "var(--heading)" }}>
                    {stage.title}
                  </h2>
                  <p className="mt-2 text-sm leading-6" style={{ color: "var(--body)" }}>
                    {stage.detail}
                  </p>
                  <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                    <KeyValue label="Bundle ID" value={bundleId || "Not started"} />
                    <KeyValue label="Selected" value={readableMetric(bundleStatus.selected_slide_count)} />
                    <KeyValue label="Downloaded" value={readableMetric(bundleStatus.downloaded_slide_count)} />
                    <KeyValue label="TFRecords" value={readableMetric(bundleStatus.tfrecord_files)} />
                    <KeyValue label="TFRecord size" value={formatBytes(numericMetric(bundleStatus.tfrecord_bytes))} />
                    <KeyValue label="Updated" value={formatEpochTime(numericMetric(bundleStatus.updated_at_epoch))} />
                  </div>
                  <div className="mt-5 rounded-[26px] border p-4" style={{ borderColor: "var(--border)", background: "rgba(244,250,255,0.92)" }}>
                    <h3 className="text-sm font-semibold uppercase tracking-[0.18em]" style={{ color: "var(--muted)" }}>
                      System message
                    </h3>
                    <p className="mt-2 text-sm leading-6" style={{ color: "var(--body)" }}>
                      {error || message}
                    </p>
                  </div>
                </div>
                <div className="rounded-[28px] border p-4" style={{ borderColor: "var(--border)", background: "linear-gradient(180deg, rgba(255,255,255,0.88), rgba(240,248,255,0.9))" }}>
                  <h3 className="text-sm font-semibold uppercase tracking-[0.18em]" style={{ color: "var(--muted)" }}>
                    Current labels
                  </h3>
                  <D3LabelBars counts={labelCounts} />
                  <div className="mt-5 grid gap-3 sm:grid-cols-2">
                    <KeyValue label="Annotations" value={String(archive?.summary?.source_annotations ?? tcgaDefaults.annotations_csv)} />
                    <KeyValue label="Bucket" value={String(archive?.summary?.bucket_uri ?? tcgaDefaults.bucket_uri)} />
                    <KeyValue label="Archive root" value={String(archive?.archive_root ?? "Waiting")} />
                    <KeyValue label="Status path" value={String(bundle?.remote_status_path ?? "Waiting")} />
                  </div>
                </div>
              </div>
            </div>
          </Panel>

          <Panel>
            <SectionTitle
              icon={<TrendingUp className="h-5 w-5" />}
              title="Approach comparison"
              label={approachChartData.length > 0 ? "live metrics" : "waiting"}
            />
            <div className="mt-5 overflow-x-auto rounded-[28px] border p-4" style={{ borderColor: "var(--card-border)", background: "rgba(255,255,255,0.78)" }}>
              {approachChartData.length > 0 ? (
                <BarChart width={540} height={300} data={approachChartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(115,149,173,0.22)" />
                  <XAxis dataKey="label" tick={{ fill: "#416989", fontSize: 12 }} axisLine={false} tickLine={false} />
                  <YAxis domain={[0, 1]} tick={{ fill: "#416989", fontSize: 12 }} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      borderRadius: 18,
                      border: "1px solid rgba(126,205,255,0.42)",
                      background: "rgba(255,255,255,0.96)",
                      color: "#14345a",
                    }}
                  />
                  <Legend />
                  <Bar dataKey="auroc" fill="#4666d9" radius={[10, 10, 0, 0]} name="AUROC" />
                  <Bar dataKey="macroF1" fill="#2b92d1" radius={[10, 10, 0, 0]} name="Macro F1" />
                  <Bar dataKey="defaultF1" fill="#d95d48" radius={[10, 10, 0, 0]} name="Default-threshold F1" />
                </BarChart>
              ) : (
                <EmptyState text="No completed Python summary is available yet for the two approaches." />
              )}
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {["Approach1", "Approach2"].map((label) => (
                <ApproachCard
                  key={label}
                  title={label === "Approach1" ? "Approach 1" : "Approach 2"}
                  subtitle={label === "Approach1" ? "TransMIL lead lane" : "Attention MIL comparison lane"}
                  metric={approachMetrics[label]}
                />
              ))}
            </div>
          </Panel>
        </section>

        <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <Panel>
            <SectionTitle
              icon={<Database className="h-5 w-5" />}
              title="Archived batch summary"
              label={String(archive?.summary?.state ?? "waiting")}
            />
            <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <KeyValue label="Batch count" value={readableMetric(archive?.summary?.batch_count)} />
              <KeyValue label="Batch size" value={readableMetric(archive?.summary?.batch_size)} />
              <KeyValue label="Completed" value={readableMetric(archive?.summary?.results_count)} />
              <KeyValue label="Finished" value={formatEpochTime(numericMetric(archive?.summary?.finished_at_epoch))} />
            </div>
            <div className="mt-4 grid gap-3">
              {["Approach1", "Approach2"].map((label) => {
                const batch = bestBatches[label];
                return (
                  <div
                    key={label}
                    className="rounded-[24px] border p-4"
                    style={{ borderColor: "var(--border)", background: "rgba(244,250,255,0.92)" }}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold" style={{ color: "var(--heading)" }}>
                          {label === "Approach1" ? "Best TransMIL batch" : "Best Attention MIL batch"}
                        </p>
                        <p className="text-xs" style={{ color: "var(--muted)" }}>
                          Highest archived AUROC from the Python batch summaries
                        </p>
                      </div>
                      <span className="rounded-full border px-3 py-1 text-xs font-semibold" style={{ borderColor: "rgba(71,167,226,0.28)", background: "rgba(71,167,226,0.12)", color: "#1f74b3" }}>
                        {batch?.bundle_id ?? "Waiting"}
                      </span>
                    </div>
                    <div className="mt-3 grid gap-2 sm:grid-cols-3">
                      <KeyValue label="AUROC" value={formatMetric(batch?.mean_auroc)} />
                      <KeyValue label="Macro F1" value={formatMetric(batch?.mean_f1_macro)} />
                      <KeyValue label="Model" value={String(batch?.mil_model ?? "Pending")} />
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="mt-5 rounded-[28px] border p-4" style={{ borderColor: "var(--border)", background: "rgba(255,255,255,0.76)" }}>
              <h3 className="text-sm font-semibold uppercase tracking-[0.18em]" style={{ color: "var(--muted)" }}>
                Batch results
              </h3>
              <div className="mt-3 grid gap-3">
                {batches.length > 0 ? (
                  batches.slice(0, 4).map((batch) => (
                    <div
                      key={String(batch.bundle_id)}
                      className="rounded-[24px] border p-4"
                      style={{ borderColor: "var(--border)", background: "rgba(244,250,255,0.92)" }}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <p className="font-semibold" style={{ color: "var(--heading)" }}>
                            {batch.bundle_id}
                          </p>
                          <p className="text-xs" style={{ color: "var(--muted)" }}>
                            {batch.slide_count ?? "?"} slides | {batch.feature_extractor_used ?? "Pending"}
                          </p>
                        </div>
                        <span className="text-xs font-semibold" style={{ color: "var(--teal)" }}>
                          {formatLabelSummary(batch.label_counts)}
                        </span>
                      </div>
                    </div>
                  ))
                ) : (
                  <EmptyState text="No batch archives are ready yet." />
                )}
              </div>
            </div>
          </Panel>

          <Panel>
            <SectionTitle
              icon={<Server className="h-5 w-5" />}
              title="Selected slide preview"
              label={selectedSlides.length > 0 ? `${selectedSlides.length} slides` : "waiting"}
            />
            <div className="mt-5 rounded-[28px] border p-4" style={{ borderColor: "var(--card-border)", background: "rgba(255,255,255,0.78)" }}>
              {selectedSlides.length > 0 ? (
                <div className="grid gap-2">
                  {selectedSlides.slice(0, 14).map((slideName) => (
                    <div
                      key={slideName}
                      className="rounded-[18px] border px-3 py-2 text-sm"
                      style={{ borderColor: "var(--border)", background: "rgba(244,250,255,0.94)", color: "var(--body)" }}
                    >
                      {slideName}
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState text="The live bundle has not materialized a slide subset yet." />
              )}
            </div>
            <div className="mt-5 grid gap-4 sm:grid-cols-3">
              <MiniSystemCard
                title="Frontend"
                detail="Single Next.js dashboard only"
                accent="#4666d9"
              />
              <MiniSystemCard
                title="Backend"
                detail="Lean Python API plus TCGA pipeline"
                accent="#2b92d1"
              />
              <MiniSystemCard
                title="Visuals"
                detail="D3 label balance and Recharts metrics"
                accent="#d95d48"
              />
            </div>
          </Panel>
        </section>
      </main>
    </div>
  );
}

function MetricCard({
  icon,
  label,
  value,
  detail,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div
      className="rounded-[28px] border p-5"
      style={{
        borderColor: "var(--card-border)",
        background:
          "linear-gradient(180deg, rgba(255,255,255,0.82), rgba(242,249,255,0.82))",
      }}
    >
      <div className="flex items-center gap-3">
        <div
          className="flex h-11 w-11 items-center justify-center rounded-2xl"
          style={{ background: "rgba(71,167,226,0.12)", color: "#1f74b3" }}
        >
          {icon}
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: "var(--muted)" }}>
            {label}
          </p>
          <p className="mt-1 text-2xl font-semibold" style={{ color: "var(--heading)" }}>
            {value}
          </p>
        </div>
      </div>
      <p className="mt-3 text-sm leading-6" style={{ color: "var(--body)" }}>
        {detail}
      </p>
    </div>
  );
}

function Panel({ children }: { children: ReactNode }) {
  return (
    <section
      className="rounded-[34px] border p-5 shadow-[0_24px_80px_rgba(90,153,194,0.14)] sm:p-6"
      style={{
        borderColor: "var(--panel-border)",
        background:
          "linear-gradient(180deg, rgba(255,255,255,0.82), rgba(243,250,255,0.84))",
      }}
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
  icon: ReactNode;
  title: string;
  label: string;
}) {
  return (
    <div className="flex items-center gap-3">
      <div
        className="flex h-11 w-11 items-center justify-center rounded-2xl"
        style={{ background: "rgba(71,167,226,0.12)", color: "#1f74b3" }}
      >
        {icon}
      </div>
      <div>
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="text-xl font-semibold" style={{ color: "var(--heading)" }}>
            {title}
          </h2>
          <span
            className="rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em]"
            style={{
              borderColor: "rgba(71,167,226,0.28)",
              background: "rgba(71,167,226,0.12)",
              color: "#1f74b3",
            }}
          >
            {label}
          </span>
        </div>
      </div>
    </div>
  );
}

function ActionButton({
  busy,
  icon,
  label,
  onClick,
}: {
  busy: boolean;
  icon: ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={busy}
      className="flex items-center justify-center gap-2 rounded-2xl border px-4 py-3 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-70"
      style={{
        borderColor: busy ? "rgba(71,167,226,0.42)" : "var(--btn-border)",
        background: busy ? "rgba(71,167,226,0.12)" : "var(--btn-bg)",
        color: "var(--btn-text)",
      }}
    >
      {icon}
      <span>{busy ? "Working..." : label}</span>
    </button>
  );
}

function ActionChip({
  icon,
  label,
}: {
  icon?: ReactNode;
  label: string;
}) {
  return (
    <span
      className="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold"
      style={{
        borderColor: "rgba(71,167,226,0.28)",
        background: "rgba(71,167,226,0.12)",
        color: "#1f74b3",
      }}
    >
      {icon}
      {label}
    </span>
  );
}

function KeyValue({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-[20px] border px-3 py-3" style={{ borderColor: "var(--border)", background: "rgba(244,250,255,0.92)" }}>
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em]" style={{ color: "var(--muted)" }}>
        {label}
      </p>
      <p className="mt-2 break-all text-sm font-semibold leading-6" style={{ color: "var(--heading)" }}>
        {value}
      </p>
    </div>
  );
}

function ApproachCard({
  title,
  subtitle,
  metric,
}: {
  title: string;
  subtitle: string;
  metric?: ApproachMetric;
}) {
  return (
    <div className="rounded-[28px] border p-4" style={{ borderColor: "var(--border)", background: "rgba(244,250,255,0.92)" }}>
      <p className="text-lg font-semibold" style={{ color: "var(--heading)" }}>
        {title}
      </p>
      <p className="mt-1 text-sm" style={{ color: "var(--muted)" }}>
        {subtitle}
      </p>
      <div className="mt-4 grid gap-2 sm:grid-cols-2">
        <KeyValue label="AUROC" value={formatMetric(metric?.mean_auroc)} />
        <KeyValue label="Macro F1" value={formatMetric(metric?.mean_f1_macro)} />
        <KeyValue label="Default F1" value={formatMetric(metric?.mean_f1_macro_default_threshold)} />
        <KeyValue label="Model" value={String(metric?.mil_model ?? "Pending")} />
      </div>
    </div>
  );
}

function MiniSystemCard({
  title,
  detail,
  accent,
}: {
  title: string;
  detail: string;
  accent: string;
}) {
  return (
    <div
      className="rounded-[24px] border p-4"
      style={{
        borderColor: "var(--border)",
        background: "rgba(255,255,255,0.8)",
        boxShadow: `inset 0 1px 0 rgba(255,255,255,0.8), 0 10px 28px ${accent}18`,
      }}
    >
      <p className="text-sm font-semibold uppercase tracking-[0.18em]" style={{ color: accent }}>
        {title}
      </p>
      <p className="mt-2 text-sm leading-6" style={{ color: "var(--body)" }}>
        {detail}
      </p>
    </div>
  );
}

function D3LabelBars({ counts }: { counts: Record<string, number> }) {
  const entries = Object.entries(counts);
  if (entries.length === 0) {
    return <EmptyState text="No MSI or MSS counts are available yet." />;
  }

  const width = 420;
  const barHeight = 26;
  const gap = 16;
  const leftPad = 86;
  const maxValue = d3Max(entries, ([, value]) => value) ?? 1;
  const scale = scaleLinear().domain([0, maxValue]).range([0, width - leftPad - 28]);
  const colors: Record<string, string> = {
    "MSI-H": "#d95d48",
    MSS: "#4666d9",
  };

  return (
    <div className="mt-4 overflow-x-auto">
      <svg width={width} height={entries.length * (barHeight + gap)}>
        {entries.map(([label, value], index) => {
          const y = index * (barHeight + gap);
          return (
            <g key={label} transform={`translate(0, ${y})`}>
              <text
                x={0}
                y={18}
                fontSize="12"
                fontWeight="700"
                fill="#416989"
              >
                {label}
              </text>
              <rect
                x={leftPad}
                y={2}
                width={width - leftPad - 20}
                height={barHeight}
                rx={13}
                fill="rgba(71,167,226,0.12)"
              />
              <rect
                x={leftPad}
                y={2}
                width={scale(value)}
                height={barHeight}
                rx={13}
                fill={colors[label] ?? "#2b92d1"}
              />
              <text
                x={leftPad + scale(value) + 10}
                y={18}
                fontSize="12"
                fontWeight="700"
                fill="#14345a"
              >
                {value}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="rounded-[22px] border p-4 text-sm" style={{ borderColor: "var(--border)", background: "rgba(244,250,255,0.92)", color: "var(--body)" }}>
      {text}
    </div>
  );
}

function tcgaStageMeta(
  state: string,
  downloadedSlides?: number,
  selectedSlides?: number,
  tfrecordFiles?: number,
  completedApproaches = 0,
) {
  const safeSelected = Math.max(selectedSlides ?? 0, 0);
  const safeDownloaded = Math.max(downloadedSlides ?? 0, 0);
  const safeTfrecords = Math.max(tfrecordFiles ?? 0, 0);
  const downloadProgress = safeSelected > 0 ? Math.min(safeDownloaded / safeSelected, 1) : 0;
  const extractionProgress = safeSelected > 0 ? Math.min(safeTfrecords / safeSelected, 1) : 0;
  const trainingProgress = Math.min(completedApproaches / 2, 1);

  switch (state) {
    case "matching_annotations":
      return {
        percent: 10,
        label: "matching",
        title: "Matching bucket slides against the DX1 annotation table",
        detail: "The Python runner is aligning the latest GCS bucket contents with the cleaned TCGA DX1 MSI annotations.",
        eta: "3 min to 8 min",
      };
    case "downloading_slides":
      return {
        percent: Math.round(18 + downloadProgress * 24),
        label: "downloading",
        title: "Downloading the selected DX1 slides",
        detail: "The VM is pulling whole-slide SVS files into the TCGA bundle workspace before preprocessing starts.",
        eta: safeSelected > 0 ? formatMinutesRange(8 + (safeSelected - safeDownloaded) * 0.4, 15 + (safeSelected - safeDownloaded) * 0.9) : "20 min to 50 min",
      };
    case "extracting_tiles":
      return {
        percent: Math.max(42, Math.round(42 + extractionProgress * 22)),
        label: "tiling",
        title: "Extracting pathology tiles and TFRecords",
        detail: `Slideflow and cucim are building TFRecords. Ready: ${safeTfrecords}/${safeSelected || "?"}.`,
        eta: safeSelected > 0 ? formatMinutesRange(12 + Math.max(safeSelected - safeTfrecords, 0) * 0.9, 25 + Math.max(safeSelected - safeTfrecords, 0) * 1.7) : "30 min to 90 min",
      };
    case "retrying_tiles":
      return {
        percent: 58,
        label: "retrying",
        title: "Retrying tile extraction with lighter QC",
        detail: "The runner is re-attempting tile extraction with a more permissive fallback instead of stopping.",
        eta: "20 min to 45 min",
      };
    case "generating_features":
      return {
        percent: 70,
        label: "features",
        title: "Generating pathology feature bags",
        detail: "Feature bags are being built for the two MSI approaches on top of the prepared TFRecords.",
        eta: safeSelected > 0 ? formatMinutesRange(10 + safeSelected * 0.08, 18 + safeSelected * 0.18) : "15 min to 35 min",
      };
    case "prepared":
      return {
        percent: 78,
        label: "prepared",
        title: "Prepared and ready for two-lane training",
        detail: "Slides, TFRecords, and feature bags are ready. The runner is about to launch the two approaches.",
        eta: "8 min to 18 min",
      };
    case "training_parallel":
      return {
        percent: Math.round(80 + trainingProgress * 18),
        label: "training",
        title: "Training Approach 1 and Approach 2",
        detail: "The single system is training TransMIL and Attention MIL in parallel on the prepared DX1 cohort.",
        eta: formatMinutesRange(6 + Math.max(2 - completedApproaches, 0) * 8, 12 + Math.max(2 - completedApproaches, 0) * 16),
      };
    case "completed":
      return {
        percent: 100,
        label: "completed",
        title: "Bundle completed",
        detail: "The latest TCGA DX1 bundle has finished and the Python metrics are available for visualization.",
        eta: "Finished",
      };
    case "failed":
      return {
        percent: 100,
        label: "failed",
        title: "Bundle failed",
        detail: "The runner stopped with an error. Use refresh to read the latest remote status and archive summary.",
        eta: "Stopped",
      };
    default:
      return {
        percent: 4,
        label: state || "ready",
        title: "Ready for the next DX1 system run",
        detail: "Only the TCGA DX1 runner remains in this interface now. Launch a run or refresh the latest Python summary.",
        eta: state ? "Pending" : "Waiting",
      };
  }
}

function readApproaches(value: unknown): Record<string, ApproachMetric> {
  if (!value || typeof value !== "object") {
    return {};
  }
  return value as Record<string, ApproachMetric>;
}

function readBestBatches(value: unknown): Record<string, BestBatchMetric> {
  if (!value || typeof value !== "object") {
    return {};
  }
  return value as Record<string, BestBatchMetric>;
}

function readLabelCounts(value: unknown): Record<string, number> {
  if (!value || typeof value !== "object") {
    return {};
  }
  return Object.fromEntries(
    Object.entries(value as Record<string, unknown>).filter((entry): entry is [string, number] => typeof entry[1] === "number"),
  );
}

function readBatches(value: unknown): BatchSummary[] {
  return Array.isArray(value) ? (value as BatchSummary[]) : [];
}

function readStringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}

function numericMetric(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function completedApproachCount(value: unknown) {
  return Array.isArray(value) ? value.length : 0;
}

function readableMetric(value: unknown) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return String(value);
  }
  if (typeof value === "string" && value.trim()) {
    return value;
  }
  return "Pending";
}

function formatEpochTime(value?: number) {
  if (!value || !Number.isFinite(value)) {
    return "Waiting";
  }
  return new Date(value * 1000).toLocaleTimeString();
}

function formatBytes(value?: number) {
  if (!value || !Number.isFinite(value) || value <= 0) {
    return "Pending";
  }
  const units = ["B", "KB", "MB", "GB", "TB"];
  let size = value;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }
  return `${size.toFixed(size >= 10 || unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

function formatMetric(value?: number | null) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "Pending";
  }
  return value.toFixed(4);
}

function formatLabelSummary(value?: Record<string, number>) {
  if (!value || Object.keys(value).length === 0) {
    return "Pending";
  }
  return Object.entries(value)
    .map(([key, count]) => `${key} ${count}`)
    .join(" | ");
}

function formatMinutesEstimate(totalMinutes: number) {
  const rounded = Math.max(1, Math.round(totalMinutes));
  if (rounded < 60) {
    return `${rounded} min`;
  }
  const hours = Math.floor(rounded / 60);
  const minutes = rounded % 60;
  return minutes === 0 ? `${hours} hr` : `${hours} hr ${minutes} min`;
}

function formatMinutesRange(minMinutes: number, maxMinutes: number) {
  const safeMin = Math.max(1, Math.round(minMinutes));
  const safeMax = Math.max(safeMin, Math.round(maxMinutes));
  return safeMin === safeMax
    ? formatMinutesEstimate(safeMin)
    : `${formatMinutesEstimate(safeMin)} to ${formatMinutesEstimate(safeMax)}`;
}
