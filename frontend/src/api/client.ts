import axios from "axios";

void import.meta.env.VITE_API_BASE_URL;

export const client = axios.create({
  baseURL: "/api",
  headers: {
    "Content-Type": "application/json",
  },
});

client.interceptors.request.use((config) => {
  // FormData 上传时让 axios/浏览器自动设置 multipart 边界，不能保留 application/json
  if (typeof FormData !== "undefined" && config.data instanceof FormData) {
    if (config.headers && typeof (config.headers as { delete?: (k: string) => void }).delete === "function") {
      (config.headers as { delete: (k: string) => void }).delete("Content-Type");
    } else if (config.headers) {
      delete (config.headers as Record<string, unknown>)["Content-Type"];
    }
  }
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
