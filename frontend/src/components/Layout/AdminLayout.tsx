import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { isAdminUser, useAuthStore } from "../../store/authStore";

interface AdminLayoutProps {
  children: React.ReactNode;
}

const NAV_ITEMS = [
  { path: "/admin/knowledge", label: "知识库", icon: "📚" },
  { path: "/admin/prompts", label: "提示词", icon: "✏️" },
  { path: "/admin/params", label: "检索参数", icon: "⚙️" },
  { path: "/admin/logs", label: "看板", icon: "📊" },
  { path: "/admin/bad-cases", label: "Bad Case", icon: "🐛" },
  { path: "/admin/agent/traces", label: "Agent 追踪", icon: "🤖" },
];

export function AdminLayout({ children }: AdminLayoutProps) {
  const location = useLocation();
  const user_id = useAuthStore((state) => state.user_id);
  const isAdmin = isAdminUser(user_id);
  const isReadOnly = !isAdmin;
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="min-h-screen flex flex-col bg-warmwhite">
      <header className="h-14 md:h-16 bg-white border-b border-gray-100 flex items-center justify-between px-3 md:px-6 shadow-sm">
        <div className="flex items-center gap-2 md:gap-3 min-w-0">
          <Link to="/admin" className="text-lg md:text-xl font-bold text-coral truncate">
            可可语伴
          </Link>
          <span className="px-2 py-0.5 rounded-full bg-coral/10 text-coral text-xs font-semibold shrink-0">
            管理后台
          </span>
        </div>

        {/* 桌面端：横向导航 */}
        <nav className="hidden md:flex items-center gap-1">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`px-3 py-2 rounded-button text-sm font-semibold transition-colors ${
                location.pathname.startsWith(item.path)
                  ? "bg-coral/10 text-coral"
                  : "text-gray-600 hover:bg-gray-100"
              }`}
            >
              <span className="mr-1">{item.icon}</span>
              {item.label}
            </Link>
          ))}
          <Link
            to="/chat"
            className="ml-2 px-3 py-2 rounded-button text-sm font-semibold text-gray-500 hover:bg-gray-100 transition-colors"
          >
            返回聊天
          </Link>
        </nav>

        {/* 移动端：汉堡菜单（右上角）*/}
        <div className="flex items-center gap-2 md:hidden">
          <Link
            to="/chat"
            className="px-2 py-2 rounded-button text-sm font-semibold text-gray-500 hover:bg-gray-100"
          >
            返回
          </Link>
          <button
            onClick={() => setMenuOpen((v) => !v)}
            className="w-10 h-10 rounded-button flex items-center justify-center text-gray-600 hover:bg-gray-100"
            aria-label="菜单"
            aria-expanded={menuOpen}
          >
            {menuOpen ? (
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18 6L6 18M6 6l12 12" strokeLinecap="round" />
              </svg>
            ) : (
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M4 6h16M4 12h16M4 18h16" strokeLinecap="round" />
              </svg>
            )}
          </button>
        </div>
      </header>

      {/* 移动端折叠菜单 */}
      {menuOpen && (
        <nav className="md:hidden bg-white border-b border-gray-100 px-3 py-2 grid grid-cols-3 gap-1">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              onClick={() => setMenuOpen(false)}
              className={`px-2 py-2.5 rounded-button text-sm font-medium text-center transition-colors ${
                location.pathname.startsWith(item.path)
                  ? "bg-coral/10 text-coral"
                  : "text-gray-600 hover:bg-gray-100"
              }`}
            >
              <span className="block text-base mb-0.5">{item.icon}</span>
              {item.label}
            </Link>
          ))}
        </nav>
      )}

      {/* 只读模式横幅（T-003：访客/非管理员）*/}
      {isReadOnly && (
        <div className="bg-amber-50 border-b border-amber-200 px-4 py-2 text-center text-xs md:text-sm text-amber-700">
          演示模式 — 仅可查看，编辑操作已禁用。
          <Link to="/login" className="ml-1 underline font-semibold">
            登录管理员账号解锁编辑
          </Link>
        </div>
      )}

      <main className="flex-1 overflow-auto p-4 md:p-6">{children}</main>
    </div>
  );
}

// 供各 Admin 页面使用：判断是否只读
export function useAdminReadOnly(): boolean {
  const user_id = useAuthStore((state) => state.user_id);
  return !isAdminUser(user_id);
}
