"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";

type Approach1Snapshot = {
  slides_total: number;
  tfrecord_files: number;
  unfinished_files: number;
  bag_files: number;
  tfrecord_bytes: number;
  bag_bytes: number;
};

type Approach2HistoryPoint = {
  epoch?: number;
  train_loss?: number;
  val_loss?: number;
  val_accuracy?: number;
  val_f1_macro?: number;
};

type StableBestResult = {
  total_evaluated: number;
  best: {
    trial_id: string;
    mean_auroc: number;
    mean_auprc: number;
    sd_auroc: number;
    stability_score: number;
    epochs?: number;
  } | null;
};

type MCPlan = {
  trials: {
    trial_id: string;
    learning_rate: number;
    dropout: number;
    epochs: number;
    feature_extractor: string;
    mil_model: string;
  }[];
};

type MonteCarloSummary = {
  mc_result_trials: number;
  dropout_ready: number;
  bootstrap_ready: number;
  total_candidates: number;
};

const palette = ["#38bdf8", "#34d399", "#f59e0b", "#f87171", "#a78bfa", "#60a5fa", "#fb7185", "#14b8a6", "#facc15"];

function formatBytes(value: number) {
  if (!value) {
    return "0 B";
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

function asNumber(value: unknown) {
  return typeof value === "number" ? value : Number(value ?? 0);
}

export function Approach1ArtifactCharts({ snapshot }: { snapshot: Approach1Snapshot }) {
  const artifactCounts = [
    { name: "Slides", value: snapshot.slides_total, fill: "#38bdf8" },
    { name: "TFRecords", value: snapshot.tfrecord_files, fill: "#34d399" },
    { name: "Unfinished", value: snapshot.unfinished_files, fill: "#f59e0b" },
    { name: "Bag files", value: snapshot.bag_files, fill: "#a78bfa" },
  ];

  const artifactBytes = [
    { name: "TFRecords", value: Number((snapshot.tfrecord_bytes / (1024 * 1024)).toFixed(2)), fill: "#0ea5e9" },
    { name: "Bags", value: Number((snapshot.bag_bytes / (1024 * 1024)).toFixed(2)), fill: "#8b5cf6" },
  ];

  return (
    <div className="grid gap-5 xl:grid-cols-2">
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={artifactCounts} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(20,53,54,0.12)" />
            <XAxis dataKey="name" tick={{ fill: "#5a7575", fontSize: 12 }} />
            <YAxis tick={{ fill: "#5a7575", fontSize: 12 }} />
            <Tooltip
              formatter={(value) => [asNumber(value).toLocaleString(), "Count"]}
              contentStyle={{ background: "#f8fffb", border: "1px solid rgba(20,53,54,0.12)", borderRadius: 12 }}
            />
            <Bar dataKey="value" radius={[10, 10, 0, 0]}>
              {artifactCounts.map((entry) => (
                <Cell key={entry.name} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={artifactBytes} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(20,53,54,0.12)" />
            <XAxis dataKey="name" tick={{ fill: "#5a7575", fontSize: 12 }} />
            <YAxis tick={{ fill: "#5a7575", fontSize: 12 }} />
            <Tooltip
              formatter={(value) => [`${asNumber(value).toFixed(2)} MB`, "Footprint"]}
              contentStyle={{ background: "#f8fffb", border: "1px solid rgba(20,53,54,0.12)", borderRadius: 12 }}
            />
            <Bar dataKey="value" radius={[10, 10, 0, 0]}>
              {artifactBytes.map((entry) => (
                <Cell key={entry.name} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="xl:col-span-2 text-sm" style={{ color: "var(--muted)" }}>
        Artifact footprint: `{formatBytes(snapshot.tfrecord_bytes)}` TFRecords and `{formatBytes(snapshot.bag_bytes)}` bags.
      </div>
    </div>
  );
}

export function Approach2AdvancedCharts({
  history,
  classDistribution,
}: {
  history: Approach2HistoryPoint[];
  classDistribution: Record<string, number>;
}) {
  const pieData = Object.entries(classDistribution).map(([name, value]) => ({ name, value }));

  return (
    <div className="grid gap-5 xl:grid-cols-2">
      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={history} margin={{ top: 8, right: 18, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(20,53,54,0.12)" />
            <XAxis dataKey="epoch" tick={{ fill: "#5a7575", fontSize: 12 }} />
            <YAxis tick={{ fill: "#5a7575", fontSize: 12 }} domain={[0, 1]} />
            <Tooltip contentStyle={{ background: "#f8fffb", border: "1px solid rgba(20,53,54,0.12)", borderRadius: 12 }} />
            <Legend />
            <Line type="monotone" dataKey="val_accuracy" name="Val accuracy" stroke="#14b8a6" strokeWidth={2.5} dot={false} />
            <Line type="monotone" dataKey="val_f1_macro" name="Macro F1" stroke="#3b82f6" strokeWidth={2.5} dot={false} />
            <Line type="monotone" dataKey="val_loss" name="Val loss" stroke="#f97316" strokeWidth={2.5} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={pieData} dataKey="value" nameKey="name" outerRadius={92} innerRadius={44} paddingAngle={2}>
              {pieData.map((entry, index) => (
                <Cell key={entry.name} fill={palette[index % palette.length]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value) => [asNumber(value).toLocaleString(), "Images"]}
              contentStyle={{ background: "#f8fffb", border: "1px solid rgba(20,53,54,0.12)", borderRadius: 12 }}
            />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function MonteCarloAdvancedCharts({
  plan,
  stableBest,
  summary,
}: {
  plan?: MCPlan;
  stableBest?: StableBestResult;
  summary: MonteCarloSummary;
}) {
  const scatterData = (plan?.trials ?? []).map((trial) => ({
    trial: trial.trial_id.slice(0, 10),
    epochs: trial.epochs,
    learningRate: Number(trial.learning_rate.toExponential(2)),
    dropout: Number((trial.dropout * 100).toFixed(1)),
  }));

  const readinessData = [
    { name: "MC result dirs", value: summary.mc_result_trials, fill: "#38bdf8" },
    { name: "Dropout ready", value: summary.dropout_ready, fill: "#34d399" },
    { name: "Bootstrap ready", value: summary.bootstrap_ready, fill: "#f59e0b" },
    { name: "Stable candidates", value: summary.total_candidates, fill: "#a78bfa" },
  ];

  const bestData = stableBest?.best
    ? [
        { name: "AUROC", value: stableBest.best.mean_auroc, fill: "#14b8a6" },
        { name: "AUPRC", value: stableBest.best.mean_auprc, fill: "#3b82f6" },
        { name: "Stability", value: stableBest.best.stability_score, fill: "#8b5cf6" },
      ]
    : [];

  return (
    <div className="grid gap-5 xl:grid-cols-2">
      <div className="h-80">
        {scatterData.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 12, right: 18, bottom: 10, left: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(20,53,54,0.12)" />
              <XAxis type="number" dataKey="epochs" name="Epochs" tick={{ fill: "#5a7575", fontSize: 12 }} />
              <YAxis type="number" dataKey="dropout" name="Dropout %" tick={{ fill: "#5a7575", fontSize: 12 }} />
              <ZAxis type="number" dataKey="learningRate" range={[70, 320]} name="Learning rate" />
              <Tooltip cursor={{ strokeDasharray: "3 3" }} contentStyle={{ background: "#f8fffb", border: "1px solid rgba(20,53,54,0.12)", borderRadius: 12 }} />
              <Scatter data={scatterData} fill="#3b82f6" name="MC plan" />
            </ScatterChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex h-full items-center justify-center text-sm" style={{ color: "var(--muted)" }}>
            Generate a Monte Carlo plan to render the stochastic search chart.
          </div>
        )}
      </div>
      <div className="grid gap-5">
        <div className="h-36">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={readinessData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(20,53,54,0.12)" />
              <XAxis dataKey="name" tick={{ fill: "#5a7575", fontSize: 11 }} />
              <YAxis tick={{ fill: "#5a7575", fontSize: 12 }} />
              <Tooltip contentStyle={{ background: "#f8fffb", border: "1px solid rgba(20,53,54,0.12)", borderRadius: 12 }} />
              <Bar dataKey="value" radius={[8, 8, 0, 0]}>
                {readinessData.map((entry) => (
                  <Cell key={entry.name} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="h-36">
          {bestData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={bestData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(20,53,54,0.12)" />
                <XAxis dataKey="name" tick={{ fill: "#5a7575", fontSize: 11 }} />
                <YAxis tick={{ fill: "#5a7575", fontSize: 12 }} domain={[0, 1]} />
                <Tooltip contentStyle={{ background: "#f8fffb", border: "1px solid rgba(20,53,54,0.12)", borderRadius: 12 }} />
                <Bar dataKey="value" radius={[8, 8, 0, 0]}>
                  {bestData.map((entry) => (
                    <Cell key={entry.name} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-full items-center justify-center text-sm" style={{ color: "var(--muted)" }}>
              Stable-best metrics will chart here once completed candidates exist.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
