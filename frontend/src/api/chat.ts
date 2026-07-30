import client from "./client";
import type { ChatResponse, MessageItem } from "../types";

export async function sendChatMessage(
  message: string,
  sessionId?: string | null
): Promise<ChatResponse> {
  const payload: { message: string; session_id?: string } = { message };
  if (sessionId) {
    payload.session_id = sessionId;
  }
  const { data } = await client.post<ChatResponse>("/chat", payload);
  return data;
}

interface MessagesResponse {
  messages: MessageItem[];
}

export async function fetchMessages(sessionId: string): Promise<MessageItem[]> {
  const { data } = await client.get<MessagesResponse>(`/sessions/${sessionId}/messages`);
  return data.messages;
}
