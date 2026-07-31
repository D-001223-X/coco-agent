import { Link, Navigate, useLocation } from "react-router-dom";
import { useAuthStore } from "../../store/authStore";

interface AdminLayoutProps {
  children: React.ReactNode;
}

const NAV_ITEMS = [
  { path: "/admin/knowledge", label: "知识库", icon: "📚" },
  { path: "/admin/prompts", label: "提示词", icon: "✏️" },
  { path: "/admin/params", label: "检索参数", icon: "⚙️" },
  { path: "/admin/logs", label: "看板", icon: "📊" },
  { path: "/admin/bad-cases", label: "Bad Case", icon: "🐛" },
];

export function AdminLayout({ children }: AdminLayoutProps) {
  const location = useLocation();
  const user_id = useAuthStore((state) => state.user_id);

  // 仅 admin（user_id == 1）可访问管理后台
  if (user_id !== 1) {
    return <Navigate to="/chat" replace />;
  }

  return (
    <div className="min-h-screen flex flex-col bg-warmwhite">
      <header className="h-16 bg-white border-b border-gray-100 flex items-center justify-between px-6 shadow-sm">
        <div className="flex items-center gap-3">
          <Link to="/admin" className="text-xl font-bold text-coral">
            可可语伴
          </Link>
          <span className="px-2 py-0.5 rounded-full bg-coral/10 text-coral text-xs font-semibold">
            管理后台
          </span>
        </div>
        <nav className="flex items-center gap-1">
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
      </header>
      <main className="flex-1 overflow-auto p-6">{children}</main>
    </div>
  );
}
