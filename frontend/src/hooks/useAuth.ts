import { useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuthStore } from "../store/authStore";

/**
 * Redirects to /login if the user is not authenticated.
 * Uses a stable guard: only navigates when the current path is NOT already /login,
 * preventing redirect loops between auth guards.
 */
export function useRequireAuth() {
  const token = useAuthStore((state) => state.token);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (!token && location.pathname !== "/login") {
      navigate("/login", { replace: true });
    }
  }, [token, navigate, location.pathname]);

  return token;
}

/**
 * Redirects to /chat if the user is already authenticated.
 * Only navigates when not already on /chat to prevent redirect loops.
 */
export function useRedirectIfAuthenticated() {
  const token = useAuthStore((state) => state.token);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (token && location.pathname !== "/chat") {
      navigate("/chat", { replace: true });
    }
  }, [token, navigate, location.pathname]);

  return token;
}
