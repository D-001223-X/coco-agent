import { useState } from "react";
import { Link } from "react-router-dom";
import { MainLayout } from "../../components/Layout/MainLayout";
import { Sidebar } from "./Sidebar";
import { ChatArea } from "./ChatArea";
import { useSessionStore } from "../../store/sessionStore";

export default function ChatPage() {
  // T-002：访客模式开放客服，移除强制登录跳转（访客用 deviceId 标识）
  const setCurrentSession = useSessionStore((state) => state.setCurrentSession);
  // P3：移动端「历史」抽屉（会话列表 + 日志入口）
  const [historyOpen, setHistoryOpen] = useState(false);

  const handleNewSession = () => {
    setCurrentSession("");
    setHistoryOpen(false);
  };

  return (
    <MainLayout>
      <div className="flex h-[calc(100vh-56px)] md:h-[calc(100vh-64px)]">
        {/* T-005 移动端隐藏会话侧栏（全屏聊天），桌面保留 */}
        <div className="hidden md:block">
          <Sidebar onNewSession={handleNewSession} />
        </div>
        <ChatArea onOpenHistory={() => setHistoryOpen(true)} />
      </div>

      {/* P3 移动端历史抽屉：会话列表 + 日志入口 */}
      {historyOpen && (
        <div className="md:hidden fixed inset-0 z-[60] bg-black/30" onClick={() => setHistoryOpen(false)}>
          <div
            className="absolute left-0 top-0 bottom-0 w-[78%] max-w-[300px] bg-white shadow-xl flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-4 border-b border-gray-100 flex items-center justify-between">
              <span className="text-base font-semibold text-gray-800">历史记录</span>
              <button
                onClick={() => setHistoryOpen(false)}
                className="w-8 h-8 rounded-button flex items-center justify-center text-gray-500 hover:bg-gray-100"
                aria-label="关闭"
              >
                ✕
              </button>
            </div>
            <div className="flex-1 overflow-hidden">
              <Sidebar onNewSession={handleNewSession} />
            </div>
            <div className="border-t border-gray-100 p-3">
              <Link
                to="/logs"
                onClick={() => setHistoryOpen(false)}
                className="flex items-center justify-center w-full py-2.5 rounded-button bg-warmwhite border border-gray-200 text-gray-700 text-sm font-semibold hover:border-coral/40 transition-colors"
              >
                📊 请求日志
              </Link>
            </div>
          </div>
        </div>
      )}
    </MainLayout>
  );
}
