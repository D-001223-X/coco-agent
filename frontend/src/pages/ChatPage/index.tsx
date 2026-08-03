import { MainLayout } from "../../components/Layout/MainLayout";
import { Sidebar } from "./Sidebar";
import { ChatArea } from "./ChatArea";
import { useSessionStore } from "../../store/sessionStore";

export default function ChatPage() {
  // T-002：访客模式开放客服，移除强制登录跳转（访客用 deviceId 标识）

  const setCurrentSession = useSessionStore((state) => state.setCurrentSession);

  const handleNewSession = () => {
    setCurrentSession("");
  };

  return (
    <MainLayout>
      <div className="flex h-[calc(100vh-56px)] md:h-[calc(100vh-64px)]">
        {/* T-005 移动端隐藏会话侧栏（全屏聊天），桌面保留 */}
        <div className="hidden md:block">
          <Sidebar onNewSession={handleNewSession} />
        </div>
        <ChatArea />
      </div>
    </MainLayout>
  );
}
