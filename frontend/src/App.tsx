import { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useAuthStore } from "./store/authStore";
import LoginPage from "./pages/LoginPage";
import ChatPage from "./pages/ChatPage";
import LogsPage from "./pages/LogsPage";

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
          <Route path="/" element={<Navigate to="/chat" replace />} />
        </Routes>
      </HydrationGate>
    </BrowserRouter>
  );
}

export default App;