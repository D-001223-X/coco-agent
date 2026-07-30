import client from "./client";
import type { LogItem, TraceDetail } from "../types";

interface LogsResponse {
  logs: LogItem[];
}

export async function fetchLogs(): Promise<LogItem[]> {
  const { data } = await client.get<LogsResponse>("/logs");
  return data.logs;
}

export async function fetchTraceDetail(traceId: string): Promise<TraceDetail> {
  const { data } = await client.get<TraceDetail>(`/logs/${traceId}`);
  return data;
}
