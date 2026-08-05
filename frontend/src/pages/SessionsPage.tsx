import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { MainLayout } from "../components/Layout/MainLayout";
import { fetchSessions } from "../api/sessions";
import { useSessionStore } from "../store/sessionStore";
import type { SessionItem } from "../types";

function formatTime(iso: string | null | undefined) {
  if (!iso) return "";
  return new Date(iso).toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function SessionsPage() {
  // R-002：访客可查看自己设备的会话列表（无需登录）
  const navigate = useNavigate();
  const setCurrentSession = useSessionStore((state) => state.setCurrentSession);
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSessions()
      .then(setSessions)
      .catch(() => setSessions([]))
      .finally(() => setLoading(false));
  }, []);

  const handleOpen = (sessionId: string) => {
    setCurrentSession(sessionId);
    navigate("/chat");
  };

  return (
    <MainLayout>
      <div className="p-6 h-[calc(100vh-64px)] overflow-y-auto custom-scrollbar">
        <div className="max-w-5xl mx-auto">
          <h1 className="text-[22px] font-semibold text-gray-800 mb-6">我的会话</h1>

          {loading && <p className="text-gray-400">加载中...</p>}

          {sessions.length === 0 && !loading && (
            <div className="bg-white rounded-card p-10 text-center shadow-sm">
              <p className="text-gray-400">暂无会话记录，去和客服聊聊吧</p>
              <button
                onClick={() => navigate("/chat")}
                className="mt-4 px-5 py-2 rounded-button bg-coral hover:bg-coral-hover text-white text-sm font-semibold transition-colors"
              >
                💬 去聊天
              </button>
            </div>
          )}

          <div className="grid gap-4">
            {sessions.map((s) => (
              <button
                key={s.session_id}
                onClick={() => handleOpen(s.session_id)}
                className="text-left bg-white rounded-card p-5 shadow-sm border border-gray-100 hover:border-coral/40 transition-colors"
              >
                <div className="flex items-center justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <p className="text-base font-semibold text-gray-800 mb-1 truncate">
                      会话 {s.session_id.slice(0, 8)}
                    </p>
                    <p className="text-xs text-gray-400">
                      {s.message_count} 条消息 · 更新于 {formatTime(s.updated_at)}
                    </p>
                  </div>
                  <span className="px-3 py-1 rounded-full bg-coral/10 text-coral text-xs font-medium shrink-0">
                    继续 →
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
