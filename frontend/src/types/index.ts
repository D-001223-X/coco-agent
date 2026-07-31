export interface LoginResponse {
  access_token: string;
  token_type: string;
  user_id: number;
  expires_in: number;
}

export interface SessionItem {
  session_id: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface MessageItem {
  id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface ChatResponse {
  session_id: string;
  message_id: number;
  response: {
    useful: boolean;
    content: string;
  };
  intent: string;
  resolved_question: string;
}

export interface LogItem {
  id: number;
  trace_id: string;
  user_id: number;
  question: string;
  intent: string;
  created_at: string;
}

export interface LogNode {
  node: string;
  input_data: unknown;
  output_data: unknown;
  duration_ms: number;
  service: string;
  status: string;
}

export interface TraceDetail {
  trace_id: string;
  user_id: number;
  nodes: LogNode[];
}

// ── Admin types ────────────────────────────────────────
export interface KnowledgeFile {
  filename: string;
  size: number;
  modified_at: string;
}

export interface KnowledgeStatus {
  chunk_count: number;
  last_build_at: string;
  index_path: string;
}

export interface PromptInfo {
  name: string;
  content: string;
  version: number;
}

export interface PromptHistoryItem {
  id: number;
  version: number;
  content: string;
  is_permanent: boolean;
  created_at: string;
  created_by: string;
}

export interface ParamsInfo {
  faiss_top_k: number;
  fts5_top_k: number;
  threshold: number;
  rrf_k: number;
  final_top_k: number;
}

export interface DashboardData {
  metrics: {
    today_requests: number;
    refusal_rate: number;
    avg_response_ms: number;
    total_logs: number;
    refusal_count: number;
  };
  trends: Array<{
    date: string;
    requests: number;
    refusal_rate: number;
  }>;
  intent_distribution: Record<string, number>;
}

export interface BadCase {
  id: number;
  trace_id: string;
  user_question: string;
  system_answer: string;
  intent: string;
  source: string;
  status: string;
  ideal_answer: string;
  created_at: string;
  updated_at: string;
  calibrated_by: string;
  stored_at: string;
}

export interface RefusePhrase {
  key: string;
  value: string;
  description: string;
}

export interface KnowledgeChunk {
  chunk_id: string;
  section: string;
  content_preview: string;
  content_full: string;
}
