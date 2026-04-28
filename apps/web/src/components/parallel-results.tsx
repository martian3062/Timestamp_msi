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

export function ParallelResults({ data }: { data: ParallelMetric[] }) {
  const d3Container = useRef<HTMLDivElement>(null);

  // Example D3 overlay or specialized chart can be added here if needed.
  // For standard comparison, Recharts is great. We'll use D3 for a supplementary visual.
  useEffect(() => {
    if (!d3Container.current) return;

    const svg = d3.select(d3Container.current);
    svg.selectAll("*").remove();
    if (!data || data.length === 0) return;

    const width = d3Container.current.clientWidth;
    const height = 60;

    const canvas = svg.append("svg").attr("width", width).attr("height", height);

    const a1Avg = d3.mean(data, d => d.Approach1 ?? undefined) || 0;
    const a2Avg = d3.mean(data, d => d.Approach2 ?? undefined) || 0;
    const mcAvg = d3.mean(data, d => d.MonteCarlo ?? undefined) || 0;

    const avgData = [
      { approach: "App 1", val: a1Avg, color: "#8884d8" },
      { approach: "App 2", val: a2Avg, color: "#82ca9d" },
      { approach: "MC", val: mcAvg, color: "#ffc658" }
    ];

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

  }, [data]);

  return (
    <div className="flex flex-col gap-4">
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
    </div>
  );
}
