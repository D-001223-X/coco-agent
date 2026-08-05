import { useEffect, useState } from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";
import { useAuthStore } from "./store/authStore";
import LoginPage from "./pages/LoginPage";
import ChatPage from "./pages/ChatPage";
import LogsPage from "./pages/LogsPage";
import SessionsPage from "./pages/SessionsPage";
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
import { RequireAdminSecret } from "./components/Admin/RequireAdminSecret";
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
// 全站访客开放：/practice/*、/chat、/sessions、/logs 扫码即用；
// /admin/* 访客只读（后端 admin_read_guest_ok 兜底写 403）。
// 登录入口：/login（通过「我的」页连击 5 次进入，R-001）
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

          {/* R-002/R-003 访客可查看会话列表与日志（无需登录）*/}
          <Route path="/sessions" element={<SessionsPage />} />
          <Route path="/logs" element={<LogsPage />} />
          <Route
            path="/admin"
            element={
              <AdminIndexPage />
            }
          />
          <Route
            path="/admin/knowledge"
            element={
              <KnowledgeAdminPage />
            }
          />
          <Route
            path="/admin/prompts"
            element={
              <PromptsAdminPage />
            }
          />
          <Route
            path="/admin/prompts/:name"
            element={
              <PromptEditPage />
            }
          />
          <Route
            path="/admin/params"
            element={
              <ParamsAdminPage />
            }
          />
          <Route
            path="/admin/logs"
            element={
              <LogsAdminPage />
            }
          />
          <Route
            path="/admin/bad-cases"
            element={
              <BadCasesAdminPage />
            }
          />
          <Route
            path="/admin/bad-cases/:id"
            element={
              <BadCaseDetailPage />
            }
          />
          <Route
            path="/admin/agent/traces"
            element={
              <AgentTracesPage />
            }
          />
          <Route
            path="/admin/agent/traces/:traceId"
            element={
              <AgentTraceDetailPage />
            }
          />

          {/* P-001 隐藏管理后台入口：/coco-admin?key=<VITE_ADMIN_SECRET> 密钥验证后重定向到 /admin */}
          <Route
            path="/coco-admin"
            element={
              <RequireAdminSecret>
                <Navigate to="/admin" replace />
              </RequireAdminSecret>
            }
          />
          <Route
            path="/coco-admin/knowledge"
            element={
              <RequireAdminSecret>
                <Navigate to="/admin/knowledge" replace />
              </RequireAdminSecret>
            }
          />
          <Route
            path="/coco-admin/prompts"
            element={
              <RequireAdminSecret>
                <Navigate to="/admin/prompts" replace />
              </RequireAdminSecret>
            }
          />
          <Route
            path="/coco-admin/params"
            element={
              <RequireAdminSecret>
                <Navigate to="/admin/params" replace />
              </RequireAdminSecret>
            }
          />
          <Route
            path="/coco-admin/logs"
            element={
              <RequireAdminSecret>
                <Navigate to="/admin/logs" replace />
              </RequireAdminSecret>
            }
          />
          <Route
            path="/coco-admin/bad-cases"
            element={
              <RequireAdminSecret>
                <Navigate to="/admin/bad-cases" replace />
              </RequireAdminSecret>
            }
          />
          <Route
            path="/coco-admin/agent/traces"
            element={
              <RequireAdminSecret>
                <Navigate to="/admin/agent/traces" replace />
              </RequireAdminSecret>
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
