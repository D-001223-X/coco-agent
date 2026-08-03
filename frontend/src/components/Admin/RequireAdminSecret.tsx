import { Navigate, useSearchParams } from "react-router-dom";

/**
 * P-001 隐藏管理后台入口：通过 /coco-admin?key=<VITE_ADMIN_SECRET> 访问。
 * 密钥不匹配/缺失 → 跳转首页。仅前端 UI 隐藏，后端 verify_admin 仍做权限兜底。
 */
export function RequireAdminSecret({ children }: { children: React.ReactNode }) {
  const [searchParams] = useSearchParams();
  const key = searchParams.get("key");
  const validKey = import.meta.env.VITE_ADMIN_SECRET;

  if (!validKey) {
    // 未配置密钥（本地 dev 无 .env 时）→ 直接放行（仍由后端校验）
    return <>{children}</>;
  }

  if (key !== validKey) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
