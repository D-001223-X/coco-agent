import client from "./client";
import type {
  KnowledgeFile,
  KnowledgeStatus,
  PromptInfo,
  PromptHistoryItem,
  ParamsInfo,
  DashboardData,
  BadCase,
} from "../types";

interface ApiResp<T> {
  code: number;
  data: T;
  msg: string;
}

// ── Knowledge base ──────────────────────────────────────
export async function fetchKnowledgeFiles(): Promise<KnowledgeFile[]> {
  const { data } = await client.get<ApiResp<{ files: KnowledgeFile[] }>>(
    "/admin/knowledge/list"
  );
  return data.data.files;
}

export async function uploadKnowledgeFile(file: File): Promise<void> {
  const form = new FormData();
  form.append("file", file);
  await client.post("/admin/knowledge/upload", form);
}

export async function deleteKnowledgeFile(filename: string): Promise<void> {
  await client.delete(`/admin/knowledge/${encodeURIComponent(filename)}`);
}

export async function rebuildKnowledgeIndex(): Promise<{ ok: boolean; message: string }> {
  const { data } = await client.post<ApiResp<{ ok: boolean; message: string }>>(
    "/admin/knowledge/rebuild"
  );
  return data.data;
}

export async function fetchKnowledgeStatus(): Promise<KnowledgeStatus> {
  const { data } = await client.get<ApiResp<KnowledgeStatus>>(
    "/admin/knowledge/status"
  );
  return data.data;
}

export interface KnowledgeChunk {
  chunk_id: string;
  section: string;
  content_preview: string;
  content_full: string;
}

export async function fetchKnowledgeChunks(): Promise<KnowledgeChunk[]> {
  const { data } = await client.get<
    ApiResp<{ chunks: KnowledgeChunk[]; total: number }>
  >("/admin/knowledge/chunks");
  return data.data.chunks;
}

// ── Prompts ────────────────────────────────────────────
export async function fetchPrompts(): Promise<PromptInfo[]> {
  const { data } = await client.get<ApiResp<{ prompts: PromptInfo[] }>>(
    "/admin/prompts"
  );
  return data.data.prompts;
}

export async function fetchPrompt(name: string): Promise<PromptInfo> {
  const { data } = await client.get<ApiResp<PromptInfo>>(
    `/admin/prompts/${name}`
  );
  return data.data;
}

export async function updatePrompt(
  name: string,
  content: string,
  makePermanent = false
): Promise<{ version: number }> {
  const { data } = await client.put<ApiResp<{ version: number }>>(
    `/admin/prompts/${name}`,
    { content, make_permanent: makePermanent }
  );
  return data.data;
}

export async function fetchPromptHistory(name: string): Promise<PromptHistoryItem[]> {
  const { data } = await client.get<ApiResp<{ history: PromptHistoryItem[] }>>(
    `/admin/prompts/${name}/history`
  );
  return data.data.history;
}

export async function restorePromptVersion(name: string, version: number): Promise<void> {
  await client.post(`/admin/prompts/${name}/restore/${version}`);
}

export async function testPrompt(
  name: string,
  question: string
): Promise<{ intent: string; response: string; resolved_question: string }> {
  const { data } = await client.post<
    ApiResp<{ intent: string; response: string; resolved_question: string }>
  >(`/admin/prompts/${name}/test`, { question });
  return data.data;
}

// ── Config (refusal phrases) ───────────────────────────
export interface RefusePhrase {
  key: string;
  value: string;
  description: string;
}

export async function fetchRefusePhrases(): Promise<Record<string, RefusePhrase>> {
  const { data } = await client.get<ApiResp<Record<string, RefusePhrase>>>(
    "/admin/config/refuse-phrases"
  );
  return data.data;
}

export async function updateRefusePhrase(
  key: string,
  value: string
): Promise<{ key: string; value: string }> {
  const { data } = await client.put<ApiResp<{ key: string; value: string }>>(
    `/admin/config/refuse-phrases/${key}`,
    { value }
  );
  return data.data;
}

// ── Params ─────────────────────────────────────────────
export async function fetchParams(): Promise<ParamsInfo> {
  const { data } = await client.get<ApiResp<ParamsInfo>>("/admin/params");
  return data.data;
}

export async function updateParams(params: Partial<ParamsInfo>): Promise<ParamsInfo> {
  const { data } = await client.put<ApiResp<ParamsInfo>>("/admin/params", params);
  return data.data;
}

export async function resetParams(): Promise<ParamsInfo> {
  const { data } = await client.post<ApiResp<ParamsInfo>>("/admin/params/reset");
  return data.data;
}

export async function saveParamsToEnv(): Promise<void> {
  await client.post("/admin/params/save");
}

// ── Dashboard ──────────────────────────────────────────
export async function fetchDashboard(): Promise<DashboardData> {
  const { data } = await client.get<ApiResp<DashboardData>>("/admin/dashboard");
  return data.data;
}

export async function markBadCase(traceId: string): Promise<void> {
  await client.post(`/admin/logs/${traceId}/badcase`);
}

// ── Bad cases ──────────────────────────────────────────
export async function fetchBadCases(
  params: { status?: string; intent?: string } = {}
): Promise<{ items: BadCase[]; total: number }> {
  const { data } = await client.get<ApiResp<{ items: BadCase[]; total: number }>>(
    "/admin/bad-cases",
    { params }
  );
  return data.data;
}

export async function fetchBadCase(id: number): Promise<BadCase> {
  const { data } = await client.get<ApiResp<BadCase>>(`/admin/bad-cases/${id}`);
  return data.data;
}

export async function updateBadCase(
  id: number,
  body: { status?: string; ideal_answer?: string }
): Promise<BadCase> {
  const { data } = await client.put<ApiResp<BadCase>>(`/admin/bad-cases/${id}`, body);
  return data.data;
}

export async function generateBadCaseDraft(id: number): Promise<string> {
  const { data } = await client.post<ApiResp<{ draft: string }>>(
    `/admin/bad-cases/${id}/generate`
  );
  return data.data.draft;
}

export async function storeBadCase(id: number): Promise<void> {
  await client.post(`/admin/bad-cases/${id}/store`);
}

// ── Agent 决策轨迹（T-007）───────────────────────────────
export interface AgentDecisionNode {
  node: "intent_recognition" | "agent_decision" | "react_loop" | "multi_agent" | "reflection";
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  duration_ms: number;
  status: "ok" | "error";
  order: number;
  service?: string;
}

export interface AgentTraceSummary {
  trace_id: string;
  user_id: number | null;
  session_id: string | null;
  query: string;
  mode: string;
  decision_path: string[];
  status: string;
  total_duration_ms: number;
  created_at: string;
}

export interface AgentTraceDetail {
  trace_id: string;
  query: string;
  mode: string;
  decision_path: AgentDecisionNode[];
  status: string;
  total_duration_ms: number;
  created_at: string;
}

export async function fetchAgentTraces(
  limit = 50,
  offset = 0
): Promise<{ traces: AgentTraceSummary[]; total: number }> {
  const { data } = await client.get<ApiResp<{ traces: AgentTraceSummary[]; total: number }>>(
    `/admin/agent/traces?limit=${limit}&offset=${offset}`
  );
  return data.data;
}

export async function fetchAgentTraceDetail(
  traceId: string
): Promise<AgentTraceDetail> {
  const { data } = await client.get<ApiResp<AgentTraceDetail>>(
    `/admin/agent/traces/${traceId}`
  );
  return data.data;
}
