import axios from "axios";
import { getDeviceId } from "../utils/deviceId";

// 部署时通过 VITE_API_BASE_URL 指向后端网关（如 CloudBase 函数域名）；
// 未设置时走同源 /api（本地 dev 由 vite proxy 转发）
const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";

export const client = axios.create({
  baseURL: API_BASE,
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
  // P-002 设备标识：所有请求自动携带 X-Device-ID（访客数据隔离）
  if (config.headers) {
    config.headers["X-Device-ID"] = getDeviceId();
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
