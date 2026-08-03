// 极简 Toast：演示环境只读提示等一次性浮层提示
let _toastTimer: ReturnType<typeof setTimeout> | null = null;

export function showToast(message: string, duration = 2500): void {
  // 移除旧的
  document.querySelectorAll(".coco-toast").forEach((el) => el.remove());
  if (_toastTimer) clearTimeout(_toastTimer);

  const el = document.createElement("div");
  el.className =
    "coco-toast fixed left-1/2 bottom-24 -translate-x-1/2 z-[100] " +
    "bg-gray-800/95 text-white text-sm px-4 py-2.5 rounded-lg shadow-lg max-w-[85vw] text-center";
  el.textContent = message;
  document.body.appendChild(el);

  _toastTimer = setTimeout(() => el.remove(), duration);
}
