import { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useAuthStore } from "./store/authStore";
import LoginPage from "./pages/LoginPage";
import ChatPage from "./pages/ChatPage";
import LogsPage from "./pages/LogsPage";
import AdminIndexPage from "./pages/Admin/AdminIndexPage";
import KnowledgeAdminPage from "./pages/Admin/KnowledgeAdminPage";
import PromptsAdminPage from "./pages/Admin/PromptsAdminPage";
import PromptEditPage from "./pages/Admin/PromptEditPage";
import ParamsAdminPage from "./pages/Admin/ParamsAdminPage";
import LogsAdminPage from "./pages/Admin/LogsAdminPage";
import BadCasesAdminPage from "./pages/Admin/BadCasesAdminPage";
import BadCaseDetailPage from "./pages/Admin/BadCaseDetailPage";
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

function App() {
  return (
    <BrowserRouter>
      <HydrationGate>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/logs" element={<LogsPage />} />
          <Route path="/admin" element={<AdminIndexPage />} />
          <Route path="/admin/knowledge" element={<KnowledgeAdminPage />} />
          <Route path="/admin/prompts" element={<PromptsAdminPage />} />
          <Route path="/admin/prompts/:name" element={<PromptEditPage />} />
          <Route path="/admin/params" element={<ParamsAdminPage />} />
          <Route path="/admin/logs" element={<LogsAdminPage />} />
          <Route path="/admin/bad-cases" element={<BadCasesAdminPage />} />
          <Route path="/admin/bad-cases/:id" element={<BadCaseDetailPage />} />
          <Route path="/practice/assessment" element={<AssessmentPage />} />
          <Route path="/practice/assessment/questions" element={<AssessmentQuestionPage />} />
          <Route path="/practice/assessment/result" element={<AssessmentResultPage />} />
          <Route path="/practice/goals" element={<GoalsPage />} />
          <Route path="/practice/plan" element={<PlanPage />} />
          <Route path="/practice/modes" element={<PracticeModesPage />} />
          <Route path="/practice/chat" element={<PracticeChatPage />} />
          <Route path="/practice/progress" element={<ProgressPage />} />
          <Route path="/" element={<Navigate to="/chat" replace />} />
        </Routes>
      </HydrationGate>
    </BrowserRouter>
  );
}

export default App;
