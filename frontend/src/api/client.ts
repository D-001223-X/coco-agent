import axios from "axios";

void import.meta.env.VITE_API_BASE_URL;

export const client = axios.create({
  baseURL: "/api",
  headers: {
    "Content-Type": "application/json",
  },
});

client.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // 同步清除 Zustand persist 的存储，防止死循环
      localStorage.removeItem("token");
      localStorage.removeItem("auth-storage");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default client;
