/**
 * Typed client for the SRAE FastAPI backend.
 *
 * Mirrors the Pydantic models in src/app/api.py. Keep these in sync.
 */

export type AnalysisReport = {
  timestamp: string;
  metric: string;
  value: number;
  status: string;
  rule_text: string;
  suggested_action: string;
  distance: number;
  explanation: string;
};

export type AnalyzeResponse = {
  total_anomalies: number;
  returned: number;
  mock_llm: boolean;
  reports: AnalysisReport[];
};

export type HealthResponse = {
  status: string;
  postgres: boolean;
  chroma: boolean;
  groq_configured: boolean;
};

export type TimeSeriesPoint = {
  timestamp: string;
  metric: string;
  value: number;
};

export type TimeSeriesResponse = {
  points: TimeSeriesPoint[];
};

const API_BASE =
  process.env.NEXT_PUBLIC_SRAE_API ?? "http://localhost:8000";

async function request<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(
      `${init?.method ?? "GET"} ${path} → ${res.status} ${res.statusText}${
        text ? `: ${text}` : ""
      }`
    );
  }
  return (await res.json()) as T;
}

export async function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export async function getTimeSeries(
  metric?: string,
  limit = 1000
): Promise<TimeSeriesResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (metric) params.set("metric", metric);
  return request<TimeSeriesResponse>(`/timeseries?${params}`);
}

export async function analyze(opts?: {
  limit?: number;
  mock?: boolean;
}): Promise<AnalyzeResponse> {
  const params = new URLSearchParams({
    limit: String(opts?.limit ?? 10),
    mock: String(opts?.mock ?? false),
  });
  return request<AnalyzeResponse>(`/analyze?${params}`, {
    method: "POST",
  });
}
