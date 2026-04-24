"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export type DistributionDatum = {
  label: string;
  value: number;
  percent: number;
  fill: string;
};

export function RechartsDistribution({ data }: { data: DistributionDatum[] }) {
  return (
    <>
      <div className="h-52 min-w-0">
        <ResponsiveContainer height="100%" width="100%">
          <BarChart data={data} layout="vertical" margin={{ left: 8, right: 8 }}>
            <CartesianGrid horizontal={false} stroke="rgba(20,53,54,0.12)" />
            <XAxis hide type="number" />
            <YAxis
              dataKey="label"
              tick={{ fill: "#315156", fontSize: 12 }}
              tickLine={false}
              type="category"
              width={92}
            />
            <Tooltip
              contentStyle={{
                background: "#f8fffb",
                border: "1px solid rgba(20,53,54,0.12)",
                borderRadius: 12,
                color: "#102b2b",
              }}
              formatter={(value) => [formatTooltipValue(value), "Rows"]}
            />
            <Bar
              dataKey="value"
              isAnimationActive={false}
              minPointSize={4}
              radius={[0, 8, 8, 0]}
            >
              {data.map((entry) => (
                <Cell fill={entry.fill} key={entry.label} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="h-40 lg:h-52">
        <ResponsiveContainer height="100%" width="100%">
          <PieChart>
            <Pie
              cx="50%"
              cy="50%"
              data={data}
              dataKey="value"
              innerRadius="58%"
              isAnimationActive={false}
              outerRadius="86%"
              paddingAngle={3}
            >
              {data.map((entry) => (
                <Cell fill={entry.fill} key={entry.label} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                background: "#f8fffb",
                border: "1px solid rgba(20,53,54,0.12)",
                borderRadius: 12,
                color: "#102b2b",
              }}
              formatter={(value) => [formatTooltipValue(value), "Rows"]}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </>
  );
}

function formatTooltipValue(value: unknown) {
  return typeof value === "number" ? value.toLocaleString() : String(value ?? "");
}
