// P-002 设备唯一标识：首次访问生成 UUID 存 localStorage，用于访客数据隔离
const DEVICE_KEY = "device_id";

function generateUuid(): string {
  // 优先使用原生 crypto.randomUUID（现代浏览器）
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  // 旧浏览器降级：手动生成 v4 UUID
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export function getDeviceId(): string {
  let deviceId = localStorage.getItem(DEVICE_KEY);
  if (!deviceId) {
    deviceId = generateUuid();
    localStorage.setItem(DEVICE_KEY, deviceId);
  }
  return deviceId;
}
