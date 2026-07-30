import { create } from "zustand";
import { sendChatMessage, fetchMessages } from "../api/chat";
import type { MessageItem, ChatResponse } from "../types";

interface ChatState {
  messagesMap: Record<string, MessageItem[]>;
  isLoading: boolean;
  loadMessages: (sessionId: string) => Promise<void>;
  sendMessage: (sessionId: string | null, content: string) => Promise<ChatResponse>;
  clearMessages: (sessionId: string) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messagesMap: {},
  isLoading: false,
  loadMessages: async (sessionId: string) => {
    set({ isLoading: true });
    try {
      const messages = await fetchMessages(sessionId);
      set((state) => ({
        messagesMap: { ...state.messagesMap, [sessionId]: messages },
      }));
    } finally {
      set({ isLoading: false });
    }
  },
  sendMessage: async (sessionId: string | null, content: string) => {
    set({ isLoading: true });
    try {
      // Optimistically add user message to current session
      const tempUserMessage: MessageItem = {
        id: Date.now(),
        role: "user",
        content,
        created_at: new Date().toISOString(),
      };

      if (sessionId) {
        set((state) => ({
          messagesMap: {
            ...state.messagesMap,
            [sessionId]: [...(state.messagesMap[sessionId] || []), tempUserMessage],
          },
        }));
      }

      const data = await sendChatMessage(content, sessionId);

      const targetSessionId = data.session_id;
      const assistantMessage: MessageItem = {
        id: data.message_id,
        role: "assistant",
        content: data.response.content,
        created_at: new Date().toISOString(),
      };

      set((state) => {
        const existing = state.messagesMap[targetSessionId] || [];
        // Remove optimistic user message if it exists in the target session
        const cleaned = existing.filter((m) => m.id !== tempUserMessage.id);
        return {
          messagesMap: {
            ...state.messagesMap,
            [targetSessionId]: [...cleaned, tempUserMessage, assistantMessage],
          },
        };
      });

      return data;
    } finally {
      set({ isLoading: false });
    }
  },
  clearMessages: (sessionId: string) => {
    set((state) => {
      const next = { ...state.messagesMap };
      delete next[sessionId];
      return { messagesMap: next };
    });
  },
}));
