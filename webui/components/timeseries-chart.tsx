"use client";

import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { AnalysisReport, TimeSeriesPoint } from "@/lib/api";

const METRIC_COLOR: Record<string, string> = {
  traffic: "#6366f1", // indigo
  sales: "#10b981", // emerald
  error_rate: "#f59e0b", // amber
};

type Row = { ts: string } & Record<string, number | string>;

function pivot(points: TimeSeriesPoint[]): {
  rows: Row[];
  metrics: string[];
} {
  const byTs = new Map<string, Row>();
  const metrics = new Set<string>();

  for (const p of points) {
    metrics.add(p.metric);
    const row = byTs.get(p.timestamp) ?? { ts: p.timestamp };
    row[p.metric] = p.value;
    byTs.set(p.timestamp, row);
  }

  const rows = Array.from(byTs.values()).sort((a, b) =>
    String(a.ts) < String(b.ts) ? -1 : 1
  );
  return { rows, metrics: Array.from(metrics) };
}

function formatTick(iso: string) {
  const d = new Date(iso);
  return `${d.getUTCMonth() + 1}/${d.getUTCDate()} ${String(d.getUTCHours()).padStart(2, "0")}h`;
}

export function TimeSeriesChart({
  points,
  anomalies,
}: {
  points: TimeSeriesPoint[];
  anomalies: AnalysisReport[];
}) {
  const { rows, metrics } = useMemo(() => pivot(points), [points]);
  const [hidden, setHidden] = useState<Set<string>>(new Set());

  const toggleMetric = (m: string) => {
    setHidden((prev) => {
      const next = new Set(prev);
      if (next.has(m)) next.delete(m);
      else next.add(m);
      return next;
    });
  };

  if (rows.length === 0) {
    return (
      <div className="h-72 flex items-center justify-center text-sm text-[var(--color-foreground-muted)]">
        No time-series data — make sure Postgres is seeded.
      </div>
    );
  }

  const visibleAnomalies = anomalies.filter((a) => !hidden.has(a.metric));

  return (
    <div className="h-80 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={rows}
          margin={{ top: 8, right: 24, bottom: 8, left: 0 }}
        >
          <CartesianGrid stroke="rgba(255,255,255,0.06)" strokeDasharray="3 3" />
          <XAxis
            dataKey="ts"
            tickFormatter={formatTick}
            tick={{ fill: "#94a3b8", fontSize: 11, fontFamily: "var(--font-fira-code)" }}
            stroke="rgba(255,255,255,0.16)"
            minTickGap={48}
          />
          <YAxis
            tick={{ fill: "#94a3b8", fontSize: 11, fontFamily: "var(--font-fira-code)" }}
            stroke="rgba(255,255,255,0.16)"
            width={56}
          />
          <Tooltip
            contentStyle={{
              background: "#0f172a",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: 8,
              fontFamily: "var(--font-fira-code)",
              fontSize: 12,
            }}
            labelStyle={{ color: "#94a3b8" }}
            labelFormatter={(label) => formatTick(String(label))}
          />
          <Legend
            wrapperStyle={{
              fontFamily: "var(--font-fira-code)",
              fontSize: 12,
              paddingTop: 8,
              cursor: "pointer",
            }}
            onClick={(o) => {
              const value = (o as { value?: string })?.value;
              if (value) toggleMetric(value);
            }}
            formatter={(value: string) => {
              const isHidden = hidden.has(value);
              return (
                <span
                  style={{
                    color: isHidden ? "#475569" : "#94a3b8",
                    textDecoration: isHidden ? "line-through" : "none",
                  }}
                >
                  {value}
                </span>
              );
            }}
          />
          {metrics.map((m) => (
            <Line
              key={m}
              type="monotone"
              dataKey={m}
              stroke={METRIC_COLOR[m] ?? "#94a3b8"}
              strokeWidth={1.5}
              dot={false}
              activeDot={{ r: 4 }}
              isAnimationActive={false}
              hide={hidden.has(m)}
            />
          ))}
          {visibleAnomalies.map((a, i) => (
            <ReferenceDot
              key={`${a.metric}-${a.timestamp}-${i}`}
              x={a.timestamp}
              y={a.value}
              r={5}
              fill={a.confidence === "low" ? "#94a3b8" : "#dc2626"}
              stroke="#fff"
              strokeWidth={1.5}
              ifOverflow="extendDomain"
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
      <p className="mt-1 text-center text-[10px] font-mono uppercase tracking-widest text-[var(--color-foreground-muted)]">
        click legend to toggle a metric · grey dot = unmatched anomaly
      </p>
    </div>
  );
}
