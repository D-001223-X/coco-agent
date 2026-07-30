import { create } from "zustand";
import { fetchLogs, fetchTraceDetail } from "../api/logs";
import type { LogItem, TraceDetail } from "../types";

interface LogState {
  logs: LogItem[];
  currentTrace: TraceDetail | null;
  isLoading: boolean;
  loadLogs: () => Promise<void>;
  loadTraceDetail: (trace_id: string) => Promise<void>;
  clearCurrentTrace: () => void;
}

export const useLogStore = create<LogState>((set) => ({
  logs: [],
  currentTrace: null,
  isLoading: false,
  loadLogs: async () => {
    set({ isLoading: true });
    try {
      const logs = await fetchLogs();
      set({ logs });
    } finally {
      set({ isLoading: false });
    }
  },
  loadTraceDetail: async (trace_id: string) => {
    set({ isLoading: true });
    try {
      const currentTrace = await fetchTraceDetail(trace_id);
      set({ currentTrace });
    } finally {
      set({ isLoading: false });
    }
  },
  clearCurrentTrace: () => set({ currentTrace: null }),
}));
