import client from "./client";
import type { SessionItem } from "../types";

interface SessionsResponse {
  sessions: SessionItem[];
}

export async function fetchSessions(): Promise<SessionItem[]> {
  const { data } = await client.get<SessionsResponse>("/sessions");
  return data.sessions;
}
