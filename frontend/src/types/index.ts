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
    translation: string;
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
