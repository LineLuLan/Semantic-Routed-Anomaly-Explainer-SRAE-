"use client";

import { useCallback, useEffect, useState } from "react";
import { Activity, AlertTriangle, Loader2, Play, Server, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardBody,
  CardHeader,
  CardSubtitle,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { TimeSeriesChart } from "@/components/timeseries-chart";
import { AnomalyCard } from "@/components/anomaly-card";
import {
  analyze,
  getHealth,
  getTimeSeries,
  type AnalyzeResponse,
  type HealthResponse,
  type TimeSeriesPoint,
} from "@/lib/api";

export default function Home() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [points, setPoints] = useState<TimeSeriesPoint[]>([]);
  const [pointsLoading, setPointsLoading] = useState(true);
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [useMock, setUseMock] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Initial: pull health + raw time-series for the chart.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [h, t] = await Promise.all([getHealth(), getTimeSeries()]);
        if (cancelled) return;
        setHealth(h);
        setPoints(t.points);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        if (!cancelled) setPointsLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const runAnalyze = useCallback(async () => {
    setAnalyzing(true);
    setError(null);
    try {
      const result = await analyze({ limit: 10, mock: useMock });
      setAnalysis(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setAnalyzing(false);
    }
  }, [useMock]);

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-10 px-4 py-10 sm:px-6 lg:px-8">
      {/* Hero */}
      <header className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs uppercase tracking-[0.18em] text-[var(--color-accent)]">
              SRAE · v0.1
            </span>
            <span className="text-xs text-[var(--color-foreground-muted)]">
              Semantic-Routed Anomaly Explainer
            </span>
          </div>
          <h1 className="font-mono text-4xl font-semibold leading-tight tracking-tight text-[var(--color-foreground)] sm:text-5xl">
            Detect. Route. <span className="text-[var(--color-primary)]">Explain.</span>
          </h1>
          <p className="max-w-xl text-sm leading-relaxed text-[var(--color-foreground-muted)]">
            IsolationForest catches the dips and spikes, ChromaDB cosine search picks
            the right playbook, and an LLM writes a one-paragraph on-call report.
            One click. Three pipelines.
          </p>
        </div>

        <div className="flex flex-col gap-2.5">
          <div className="flex items-center gap-2">
            <Button
              onClick={runAnalyze}
              disabled={analyzing}
              size="lg"
              className="min-w-[180px]"
            >
              {analyzing ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Analyzing…
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  Analyze
                </>
              )}
            </Button>
          </div>
          <label className="flex items-center gap-2 text-xs font-mono text-[var(--color-foreground-muted)] select-none">
            <input
              type="checkbox"
              checked={useMock}
              onChange={(e) => setUseMock(e.target.checked)}
              className="h-3.5 w-3.5 accent-[var(--color-primary)]"
            />
            Mock LLM (fast, deterministic)
          </label>
        </div>
      </header>

      {/* Status strip */}
      <StatusStrip health={health} />

      {error && (
        <Card className="border-red-500/30 bg-red-500/5">
          <CardBody className="flex items-start gap-3 py-4">
            <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-400" />
            <div className="space-y-1">
              <p className="text-sm font-medium text-red-300">Request failed</p>
              <p className="font-mono text-xs text-red-200/70">{error}</p>
            </div>
          </CardBody>
        </Card>
      )}

      {/* Time-series chart */}
      <Card>
        <CardHeader>
          <div>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-[var(--color-accent)]" />
              Time-series — last 7 days
            </CardTitle>
            <CardSubtitle>
              traffic · sales · error_rate · 168 hourly points each ·
              red dots = detected anomalies
            </CardSubtitle>
          </div>
        </CardHeader>
        <CardBody>
          {pointsLoading ? (
            <Skeleton className="h-72 w-full" />
          ) : (
            <TimeSeriesChart
              points={points}
              anomalies={analysis?.reports ?? []}
            />
          )}
        </CardBody>
      </Card>

      {/* Reports */}
      <section className="space-y-4">
        <div className="flex items-end justify-between border-b border-[var(--color-border)] pb-3">
          <div>
            <h2 className="font-mono text-lg font-semibold text-[var(--color-foreground)]">
              Anomaly reports
            </h2>
            <p className="text-xs text-[var(--color-foreground-muted)]">
              {analysis
                ? `Showing ${analysis.returned} of ${analysis.total_anomalies} flagged anomalies${
                    analysis.mock_llm ? " · mock LLM" : " · live LLM"
                  }`
                : "Click Analyze to run the pipeline."}
            </p>
          </div>
          {analysis && (
            <Badge tone={analysis.mock_llm ? "neutral" : "info"}>
              <Sparkles className="h-3 w-3" />
              {analysis.mock_llm ? "mock" : "groq"}
            </Badge>
          )}
        </div>

        {analyzing && <AnalyzingSkeleton />}

        {!analyzing && !analysis && (
          <Card>
            <CardBody className="py-12 text-center">
              <p className="text-sm text-[var(--color-foreground-muted)]">
                No analysis yet. Hit{" "}
                <span className="font-mono text-[var(--color-primary)]">
                  Analyze
                </span>{" "}
                to detect, route, and explain.
              </p>
            </CardBody>
          </Card>
        )}

        {!analyzing && analysis && analysis.reports.length === 0 && (
          <Card>
            <CardBody className="py-12 text-center">
              <p className="text-sm text-[var(--color-foreground-muted)]">
                No anomalies flagged. The system is healthy.
              </p>
            </CardBody>
          </Card>
        )}

        {!analyzing &&
          analysis &&
          analysis.reports.map((r, i) => (
            <AnomalyCard
              key={`${r.metric}-${r.timestamp}-${i}`}
              report={r}
            />
          ))}
      </section>

      <footer className="border-t border-[var(--color-border)] pt-6 pb-2 text-xs font-mono text-[var(--color-foreground-muted)]">
        Postgres · ChromaDB · IsolationForest · all-MiniLM-L6-v2 ·
        Groq Llama-3 · FastAPI · Next.js
      </footer>
    </div>
  );
}

function StatusStrip({ health }: { health: HealthResponse | null }) {
  if (!health) {
    return (
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-16" />
        ))}
      </div>
    );
  }
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <StatusCell
        label="Status"
        value={health.status}
        tone={health.status === "ok" ? "success" : "warning"}
      />
      <StatusCell
        label="Postgres"
        value={health.postgres ? "online" : "offline"}
        tone={health.postgres ? "success" : "danger"}
      />
      <StatusCell
        label="Chroma"
        value={health.chroma ? "ready" : "missing"}
        tone={health.chroma ? "success" : "danger"}
      />
      <StatusCell
        label="Groq"
        value={health.groq_configured ? "configured" : "off"}
        tone={health.groq_configured ? "info" : "neutral"}
      />
    </div>
  );
}

function StatusCell({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: "success" | "danger" | "warning" | "info" | "neutral";
}) {
  return (
    <Card className="px-4 py-3">
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--color-foreground-muted)]">
          <Server className="mr-1 inline h-3 w-3" />
          {label}
        </span>
        <Badge tone={tone}>{value}</Badge>
      </div>
    </Card>
  );
}

function AnalyzingSkeleton() {
  return (
    <div className="space-y-4">
      {[0, 1, 2].map((i) => (
        <Skeleton key={i} className="h-44" />
      ))}
    </div>
  );
}
