import { create } from "zustand";
import { persist } from "zustand/middleware";
import { login as loginApi } from "../api/auth";

interface AuthState {
  token: string | null;
  user_id: number | null;
  expires_in: number | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user_id: null,
      expires_in: null,
      login: async (email: string, password: string) => {
        const data = await loginApi(email, password);
        // Store token for axios interceptor (read-only key)
        localStorage.setItem("token", data.access_token);
        set({
          token: data.access_token,
          user_id: data.user_id,
          expires_in: data.expires_in,
        });
      },
      logout: () => {
        localStorage.removeItem("token");
        localStorage.removeItem("auth-storage");
        set({ token: null, user_id: null, expires_in: null });
      },
    }),
    {
      name: "auth-storage",
      partialize: (state) => ({
        token: state.token,
        user_id: state.user_id,
        expires_in: state.expires_in,
      }),
    }
  )
);
