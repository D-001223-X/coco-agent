import { useState } from "react";
import { isAdminUser, useAuthStore } from "../store/authStore";
import { showToast } from "../utils/toast";

const READONLY_TOAST = "演示环境仅可查看，如需编辑请登录管理员账号。";

/**
 * T-003 管理后台访客只读模式
 * - readOnly: 非管理员时为 true（编辑操作禁用）
 * - guard(): 包装写操作，只读时弹 Toast 并拦截
 * - readonlyProps: 便捷透传给按钮的 {disabled, title}
 */
export function useReadOnlyGuard() {
  const user_id = useAuthStore((state) => state.user_id);
  const [readOnly] = useState(() => !isAdminUser(user_id));

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const guard = <T extends any[]>(fn: (...args: T) => unknown) => {
    return (...args: T): unknown => {
      if (readOnly) {
        showToast(READONLY_TOAST);
        return undefined;
      }
      return fn(...args);
    };
  };

  return { readOnly, guard, readonlyProps: { disabled: readOnly, title: readOnly ? "演示模式，仅可查看" : undefined } };
}
