import { create } from "zustand";
import { fetchSessions } from "../api/sessions";
import type { SessionItem } from "../types";

interface SessionState {
  sessions: SessionItem[];
  currentSessionId: string | null;
  isLoading: boolean;
  loadSessions: () => Promise<void>;
  setCurrentSession: (id: string) => void;
  clearSessions: () => void;
  addOrUpdateSession: (session: SessionItem) => void;
}

export const useSessionStore = create<SessionState>((set, get) => ({
  sessions: [],
  currentSessionId: null,
  isLoading: false,
  loadSessions: async () => {
    set({ isLoading: true });
    try {
      const sessions = await fetchSessions();
      set({ sessions });
    } finally {
      set({ isLoading: false });
    }
  },
  setCurrentSession: (id: string) => set({ currentSessionId: id }),
  clearSessions: () => set({ sessions: [], currentSessionId: null }),
  addOrUpdateSession: (session: SessionItem) => {
    const { sessions } = get();
    const exists = sessions.find((s) => s.session_id === session.session_id);
    let nextSessions: SessionItem[];
    if (exists) {
      nextSessions = sessions.map((s) =>
        s.session_id === session.session_id ? session : s
      );
    } else {
      nextSessions = [session, ...sessions];
    }
    set({ sessions: nextSessions, currentSessionId: session.session_id });
  },
}));
