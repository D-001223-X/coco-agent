import { useEffect } from "react";
import { MessageList } from "./MessageList";
import { MessageInput } from "./MessageInput";
import { useChatStore } from "../../../store/chatStore";
import { useSessionStore } from "../../../store/sessionStore";


export function ChatArea() {
  const currentSessionId = useSessionStore((state) => state.currentSessionId);
  const setCurrentSession = useSessionStore((state) => state.setCurrentSession);
  const loadSessions = useSessionStore((state) => state.loadSessions);

  const messagesMap = useChatStore((state) => state.messagesMap);
  const isLoading = useChatStore((state) => state.isLoading);
  const loadMessages = useChatStore((state) => state.loadMessages);
  const sendMessage = useChatStore((state) => state.sendMessage);

  const messages = currentSessionId ? messagesMap[currentSessionId] || [] : [];

  useEffect(() => {
    if (currentSessionId) {
      loadMessages(currentSessionId);
    }
  }, [currentSessionId, loadMessages]);

  const handleSend = async (content: string) => {
    const data = await sendMessage(currentSessionId, content);
    // 首次发送（无会话）：后端返回新 session_id，立即切换到该会话，
    // 否则页面停留在空白初始状态（currentSessionId 仍为空）。
    if (data.session_id && data.session_id !== currentSessionId) {
      setCurrentSession(data.session_id);
    }
    // Refresh session list to show new session and updated message counts
    await loadSessions();
  };

  return (
    <div className="flex-1 flex flex-col bg-warmwhite">
      <div className="h-14 px-6 bg-white border-b border-gray-100 flex items-center shadow-sm">
        <h2 className="text-base font-semibold text-gray-800">
          {currentSessionId
            ? `会话 ${currentSessionId.slice(0, 8)}`
            : "请选择或新建会话"}
        </h2>
      </div>
      <MessageList messages={messages} isLoading={isLoading} />
      <MessageInput onSend={handleSend} disabled={isLoading} />
    </div>
  );
}
