import { useEffect } from "react";
import { useSessionStore } from "../../../store/sessionStore";
import type { SessionItem } from "../../../types";

interface SidebarProps {
  onNewSession: () => void;
}

function formatTime(iso: string) {
  const date = new Date(iso);
  return date.toLocaleString("zh-CN", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function Sidebar({ onNewSession }: SidebarProps) {
  const sessions = useSessionStore((state) => state.sessions);
  const currentSessionId = useSessionStore((state) => state.currentSessionId);
  const isLoading = useSessionStore((state) => state.isLoading);
  const loadSessions = useSessionStore((state) => state.loadSessions);
  const setCurrentSession = useSessionStore((state) => state.setCurrentSession);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  return (
    <aside className="w-[260px] min-w-[260px] bg-white border-r border-gray-100 flex flex-col">
      <div className="p-4 border-b border-gray-100">
        <button
          onClick={onNewSession}
          className="w-full py-2.5 rounded-button bg-coral hover:bg-coral-hover text-white font-semibold transition-colors shadow-sm"
        >
          + 新会话
        </button>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar p-3">
        {isLoading && sessions.length === 0 && (
          <p className="text-center text-gray-400 text-sm py-4">加载中...</p>
        )}

        {sessions.length === 0 && !isLoading && (
          <p className="text-center text-gray-400 text-sm py-4">暂无会话</p>
        )}

        <div className="flex flex-col gap-2">
          {sessions.map((session: SessionItem) => (
            <button
              key={session.session_id}
              onClick={() => setCurrentSession(session.session_id)}
              className={`w-full text-left px-4 py-3 rounded-card transition-all ${
                session.session_id === currentSessionId
                  ? "bg-coral/10 border border-coral/20"
                  : "bg-gray-50 hover:bg-gray-100 border border-transparent"
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-gray-400">
                  {formatTime(session.updated_at)}
                </span>
                {session.message_count > 0 && (
                  <span className="text-xs text-coral font-medium">
                    {session.message_count} 条
                  </span>
                )}
              </div>
              <p className="text-sm text-gray-700 truncate">
                会话 {session.session_id.slice(0, 8)}
              </p>
            </button>
          ))}
        </div>
      </div>
    </aside>
  );
}
