"use client";

import { useEffect, useRef } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import * as d3 from "d3";

export type ParallelMetric = {
  name: string;
  Approach1: number | null;
  Approach2: number | null;
  MonteCarlo: number | null;
};

type MetricKey = "Approach1" | "Approach2" | "MonteCarlo";

const approachMeta: Array<{
  key: MetricKey;
  shortLabel: string;
  label: string;
  color: string;
  accent: string;
}> = [
  {
    key: "Approach1",
    shortLabel: "A1",
    label: "Approach 1",
    color: "#8884d8",
    accent: "#ebe9ff",
  },
  {
    key: "Approach2",
    shortLabel: "A2",
    label: "Approach 2",
    color: "#82ca9d",
    accent: "#e6faf0",
  },
  {
    key: "MonteCarlo",
    shortLabel: "MC",
    label: "Monte Carlo",
    color: "#ffc658",
    accent: "#fff6df",
  },
];

function formatMetricValue(value: number | null) {
  if (value === null || Number.isNaN(value)) {
    return "--";
  }
  return value.toFixed(value >= 0.99 ? 4 : 3);
}

export function ParallelResults({ data }: { data: ParallelMetric[] }) {
  const d3Container = useRef<HTMLDivElement>(null);
  const averages = approachMeta.map((approach) => {
    const values = data
      .map((metric) => metric[approach.key])
      .filter((value): value is number => value !== null && Number.isFinite(value));

    return {
      ...approach,
      mean: values.length > 0 ? d3.mean(values) ?? 0 : 0,
      count: values.length,
    };
  });

  const metricWinners = data.map((metric) => {
    const ranked = approachMeta
      .map((approach) => ({
        ...approach,
        value: metric[approach.key],
      }))
      .filter((entry): entry is typeof approachMeta[number] & { value: number } => entry.value !== null && Number.isFinite(entry.value))
      .sort((left, right) => right.value - left.value);

    return {
      metric: metric.name,
      winner: ranked[0] ?? null,
      runnerUp: ranked[1] ?? null,
      spread:
        ranked.length > 1 && ranked[0] && ranked[1]
          ? ranked[0].value - ranked[1].value
          : null,
    };
  });

  useEffect(() => {
    if (!d3Container.current) return;

    const svg = d3.select(d3Container.current);
    svg.selectAll("*").remove();
    if (!data || data.length === 0) return;

    const width = d3Container.current.clientWidth;
    const height = 60;

    const canvas = svg.append("svg").attr("width", width).attr("height", height);
    const avgData = averages.map((approach) => ({
      approach: approach.shortLabel,
      val: approach.mean,
      color: approach.color,
    }));

    const x = d3.scaleLinear().domain([0, 1]).range([0, width - 60]);
    const y = d3.scaleBand().domain(avgData.map(d => d.approach)).range([0, height]).padding(0.1);

    const g = canvas.append("g").attr("transform", "translate(40, 0)");

    g.selectAll("rect")
      .data(avgData)
      .enter()
      .append("rect")
      .attr("y", d => y(d.approach)!)
      .attr("height", y.bandwidth())
      .attr("fill", d => d.color)
      .attr("x", 0)
      .attr("width", 0)
      .transition()
      .duration(800)
      .attr("width", d => x(d.val));

    g.selectAll("text")
      .data(avgData)
      .enter()
      .append("text")
      .attr("y", d => y(d.approach)! + y.bandwidth() / 2 + 4)
      .attr("x", -35)
      .style("font-size", "10px")
      .style("fill", "#315156")
      .text(d => d.approach);

  }, [averages, data]);

  return (
    <div className="flex flex-col gap-4">
      <div className="grid gap-3 lg:grid-cols-3">
        {averages.map((approach) => (
          <div
            key={approach.key}
            className="rounded-3xl border p-4"
            style={{
              borderColor: "rgba(20,53,54,0.12)",
              background: approach.accent,
            }}
          >
            <div className="flex items-center justify-between gap-3">
              <span className="text-sm font-semibold" style={{ color: "#143536" }}>
                {approach.label}
              </span>
              <span
                className="rounded-full px-2 py-1 text-[11px] font-semibold uppercase"
                style={{ background: "rgba(255,255,255,0.72)", color: approach.color }}
              >
                {approach.count} metrics
              </span>
            </div>
            <p className="mt-3 text-3xl font-semibold" style={{ color: approach.color }}>
              {formatMetricValue(approach.mean)}
            </p>
            <p className="mt-1 text-xs leading-5" style={{ color: "#4f6468" }}>
              Mean score across all available advanced comparison metrics.
            </p>
          </div>
        ))}
      </div>

      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(20,53,54,0.12)" />
            <XAxis dataKey="name" tick={{ fill: "#315156" }} />
            <YAxis tick={{ fill: "#315156" }} domain={[0, 1]} />
            <Tooltip
              contentStyle={{
                background: "#f8fffb",
                border: "1px solid rgba(20,53,54,0.12)",
                borderRadius: 8,
              }}
            />
            <Legend />
            <Bar dataKey="Approach1" fill="#8884d8" name="Approach 1 (Baseline)" radius={[4, 4, 0, 0]} />
            <Bar dataKey="Approach2" fill="#82ca9d" name="Approach 2 (Platform)" radius={[4, 4, 0, 0]} />
            <Bar dataKey="MonteCarlo" fill="#ffc658" name="Approach 3 (Monte Carlo)" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      
      <div className="mt-4 flex flex-col gap-2">
        <span className="text-sm font-semibold text-teal-900">Average Performance Snapshot (D3.js)</span>
        <div ref={d3Container} className="w-full h-[60px]" />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="overflow-hidden rounded-3xl border" style={{ borderColor: "rgba(20,53,54,0.12)" }}>
          <div className="border-b px-4 py-3" style={{ borderColor: "rgba(20,53,54,0.12)", background: "#f8fffb" }}>
            <p className="text-sm font-semibold" style={{ color: "#143536" }}>
              Metric Matrix
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead style={{ background: "rgba(20,53,54,0.04)", color: "#315156" }}>
                <tr>
                  <th className="px-4 py-3 text-left font-semibold">Metric</th>
                  {approachMeta.map((approach) => (
                    <th key={approach.key} className="px-4 py-3 text-left font-semibold">
                      {approach.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.map((metric) => (
                  <tr key={metric.name} className="border-t" style={{ borderColor: "rgba(20,53,54,0.08)" }}>
                    <td className="px-4 py-3 font-medium" style={{ color: "#143536" }}>
                      {metric.name}
                    </td>
                    {approachMeta.map((approach) => {
                      const value = metric[approach.key];
                      return (
                        <td key={`${metric.name}-${approach.key}`} className="px-4 py-3" style={{ color: "#4f6468" }}>
                          {formatMetricValue(value)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="rounded-3xl border p-4" style={{ borderColor: "rgba(20,53,54,0.12)", background: "#f8fffb" }}>
          <p className="text-sm font-semibold" style={{ color: "#143536" }}>
            Best Per Metric
          </p>
          <div className="mt-4 grid gap-3">
            {metricWinners.map((entry) => (
              <div
                key={entry.metric}
                className="rounded-2xl border px-4 py-3"
                style={{ borderColor: "rgba(20,53,54,0.1)", background: "rgba(255,255,255,0.92)" }}
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm font-semibold" style={{ color: "#143536" }}>
                    {entry.metric}
                  </span>
                  {entry.winner ? (
                    <span
                      className="rounded-full px-2 py-1 text-[11px] font-semibold uppercase"
                      style={{ background: entry.winner.accent, color: entry.winner.color }}
                    >
                      {entry.winner.label}
                    </span>
                  ) : null}
                </div>
                <p className="mt-2 text-xs leading-5" style={{ color: "#4f6468" }}>
                  {entry.winner
                    ? `Lead ${formatMetricValue(entry.winner.value)}`
                    : "No completed artifact value available yet."}
                  {entry.runnerUp && entry.spread !== null
                    ? ` | Margin ${formatMetricValue(entry.spread)} over ${entry.runnerUp.label}.`
                    : ""}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
