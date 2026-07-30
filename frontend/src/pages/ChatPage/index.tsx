import { MainLayout } from "../../components/Layout/MainLayout";
import { Sidebar } from "./Sidebar";
import { ChatArea } from "./ChatArea";
import { useRequireAuth } from "../../hooks/useAuth";
import { useSessionStore } from "../../store/sessionStore";

export default function ChatPage() {
  useRequireAuth();

  const setCurrentSession = useSessionStore((state) => state.setCurrentSession);

  const handleNewSession = () => {
    setCurrentSession("");
  };

  return (
    <MainLayout>
      <div className="flex h-[calc(100vh-64px)]">
        <Sidebar onNewSession={handleNewSession} />
        <ChatArea />
      </div>
    </MainLayout>
  );
}
