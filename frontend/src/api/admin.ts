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

export async function rebuildKnowledgeIndex(): Promise<void> {
  await client.post("/admin/knowledge/rebuild");
}

export async function fetchKnowledgeStatus(): Promise<KnowledgeStatus> {
  const { data } = await client.get<ApiResp<KnowledgeStatus>>(
    "/admin/knowledge/status"
  );
  return data.data;
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
