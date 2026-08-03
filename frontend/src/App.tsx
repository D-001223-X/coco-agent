import { useEffect, useState } from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  useLocation,
} from "react-router-dom";
import { useAuthStore } from "./store/authStore";
import LoginPage from "./pages/LoginPage";
import ChatPage from "./pages/ChatPage";
import LogsPage from "./pages/LogsPage";
import ProfilePage from "./pages/ProfilePage";
import AdminIndexPage from "./pages/Admin/AdminIndexPage";
import KnowledgeAdminPage from "./pages/Admin/KnowledgeAdminPage";
import PromptsAdminPage from "./pages/Admin/PromptsAdminPage";
import PromptEditPage from "./pages/Admin/PromptEditPage";
import ParamsAdminPage from "./pages/Admin/ParamsAdminPage";
import LogsAdminPage from "./pages/Admin/LogsAdminPage";
import BadCasesAdminPage from "./pages/Admin/BadCasesAdminPage";
import BadCaseDetailPage from "./pages/Admin/BadCaseDetailPage";
import AgentTracesPage from "./pages/Admin/AgentTracesPage";
import AgentTraceDetailPage from "./pages/Admin/AgentTraceDetailPage";
import AssessmentPage from "./pages/Practice/AssessmentPage";
import AssessmentQuestionPage from "./pages/Practice/AssessmentQuestionPage";
import AssessmentResultPage from "./pages/Practice/AssessmentResultPage";
import GoalsPage from "./pages/Practice/GoalsPage";
import PlanPage from "./pages/Practice/PlanPage";
import PracticeModesPage from "./pages/Practice/PracticeModesPage";
import PracticeChatPage from "./pages/Practice/PracticeChatPage";
import ProgressPage from "./pages/Practice/ProgressPage";

// Hydration gate: waits for Zustand persist to finish reading from
// localStorage before rendering any route. Prevents the initial
// token=null flash that would otherwise trigger a spurious redirect.
function HydrationGate({ children }: { children: React.ReactNode }) {
  const [hydrated, setHydrated] = useState(() => useAuthStore.persist.hasHydrated());

  useEffect(() => {
    if (hydrated) return;
    const unsub = useAuthStore.persist.onFinishHydration(() => {
      setHydrated(true);
    });
    // If hydration already happened between render and effect, ensure we flip.
    if (useAuthStore.persist.hasHydrated()) {
      setHydrated(true);
    }
    return unsub;
  }, [hydrated]);

  if (!hydrated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-warmwhite">
        <p className="text-gray-400">加载中...</p>
      </div>
    );
  }

  return <>{children}</>;
}

// ── 路由守卫（T-访客模式）───────────────────────────────
// /practice/* 为访客路线（扫码即用，无需登录）
// /admin/* 需登录（且后端校验 admin 角色）
// 其余（/chat /logs /profile）需登录
function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((state) => state.token);
  const location = useLocation();
  if (!token) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return <>{children}</>;
}

function App() {
  const token = useAuthStore((state) => state.token);

  return (
    <BrowserRouter>
      <HydrationGate>
        <Routes>
          {/* 登录页：已登录跳转聊天 */}
          <Route
            path="/login"
            element={token ? <Navigate to="/chat" replace /> : <LoginPage />}
          />

          {/* 访客路线：/practice/* 与 /profile 无需登录（扫码即用） */}
          <Route path="/practice/assessment" element={<AssessmentPage />} />
          <Route path="/practice/assessment/questions" element={<AssessmentQuestionPage />} />
          <Route path="/practice/assessment/result" element={<AssessmentResultPage />} />
          <Route path="/practice/goals" element={<GoalsPage />} />
          <Route path="/practice/plan" element={<PlanPage />} />
          <Route path="/practice/modes" element={<PracticeModesPage />} />
          <Route path="/practice/chat" element={<PracticeChatPage />} />
          <Route path="/practice/progress" element={<ProgressPage />} />
          <Route path="/practice" element={<Navigate to="/practice/assessment" replace />} />
          <Route path="/profile" element={<ProfilePage />} />

          {/* 访客客服：/chat 无需登录（T-002，deviceId 标识访客）*/}
          <Route path="/chat" element={<ChatPage />} />

          {/* 需登录：日志/管理后台 */}
          <Route
            path="/logs"
            element={
              <RequireAuth>
                <LogsPage />
              </RequireAuth>
            }
          />
          <Route
            path="/admin"
            element={
              <RequireAuth>
                <AdminIndexPage />
              </RequireAuth>
            }
          />
          <Route
            path="/admin/knowledge"
            element={
              <RequireAuth>
                <KnowledgeAdminPage />
              </RequireAuth>
            }
          />
          <Route
            path="/admin/prompts"
            element={
              <RequireAuth>
                <PromptsAdminPage />
              </RequireAuth>
            }
          />
          <Route
            path="/admin/prompts/:name"
            element={
              <RequireAuth>
                <PromptEditPage />
              </RequireAuth>
            }
          />
          <Route
            path="/admin/params"
            element={
              <RequireAuth>
                <ParamsAdminPage />
              </RequireAuth>
            }
          />
          <Route
            path="/admin/logs"
            element={
              <RequireAuth>
                <LogsAdminPage />
              </RequireAuth>
            }
          />
          <Route
            path="/admin/bad-cases"
            element={
              <RequireAuth>
                <BadCasesAdminPage />
              </RequireAuth>
            }
          />
          <Route
            path="/admin/bad-cases/:id"
            element={
              <RequireAuth>
                <BadCaseDetailPage />
              </RequireAuth>
            }
          />
          <Route
            path="/admin/agent/traces"
            element={
              <RequireAuth>
                <AgentTracesPage />
              </RequireAuth>
            }
          />
          <Route
            path="/admin/agent/traces/:traceId"
            element={
              <RequireAuth>
                <AgentTraceDetailPage />
              </RequireAuth>
            }
          />

          {/* 根路径：已登录 → /chat，访客 → /practice/assessment */}
          <Route
            path="/"
            element={
              token ? (
                <Navigate to="/chat" replace />
              ) : (
                <Navigate to="/practice/assessment" replace />
              )
            }
          />
        </Routes>
      </HydrationGate>
    </BrowserRouter>
  );
}

export default App;
