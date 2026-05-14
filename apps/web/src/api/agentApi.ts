import type { AgentResponse, ContextRequest, GraphNode, MetricsData } from "@/types/agent";

const BASE = "/api";

export async function runAgent(
  ctx: ContextRequest,
  image?: File,
  video?: File
): Promise<AgentResponse> {
  const form = new FormData();
  form.append("context_json", JSON.stringify(ctx));
  if (image) form.append("image", image);
  if (video) form.append("video", video);

  const res = await fetch(`${BASE}/agent/run`, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Agent API error ${res.status}: ${err}`);
  }
  return res.json() as Promise<AgentResponse>;
}

export async function getGraphNodes(): Promise<{ nodes: GraphNode[]; edges: unknown[] }> {
  const res = await fetch(`${BASE}/graph/nodes`);
  if (!res.ok) throw new Error(`Graph API error ${res.status}`);
  return res.json();
}

export async function queryGraph(keyword: string): Promise<{ results: GraphNode[]; count: number }> {
  const res = await fetch(`${BASE}/graph/query?keyword=${encodeURIComponent(keyword)}`);
  if (!res.ok) throw new Error(`Graph query error ${res.status}`);
  return res.json();
}

export async function getMetrics(): Promise<MetricsData> {
  const res = await fetch(`${BASE}/logs/metrics`);
  if (!res.ok) throw new Error(`Metrics API error ${res.status}`);
  return res.json();
}

export async function getLogs(limit = 50): Promise<{ logs: unknown[] }> {
  const res = await fetch(`${BASE}/logs/?limit=${limit}`);
  if (!res.ok) throw new Error(`Logs API error ${res.status}`);
  return res.json();
}
