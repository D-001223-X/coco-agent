import { Link, useLocation } from "react-router-dom";
import { useAuthStore } from "../../store/authStore";

interface MainLayoutProps {
  children: React.ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
  const location = useLocation();
  const logout = useAuthStore((state) => state.logout);
  const user_id = useAuthStore((state) => state.user_id);

  const navItems = [
    { path: "/chat", label: "聊天" },
    { path: "/logs", label: "日志" },
  ];
  // 仅 admin 可见管理后台入口
  if (user_id === 1) {
    navItems.push({ path: "/admin", label: "管理后台" });
  }

  return (
    <div className="min-h-screen flex flex-col bg-warmwhite">
      <header className="h-16 bg-white border-b border-gray-100 flex items-center justify-between px-6 shadow-sm">
        <Link to="/chat" className="text-xl font-bold text-coral">
          可可语伴
        </Link>
        <nav className="flex items-center gap-2">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`px-4 py-2 rounded-button text-sm font-semibold transition-colors ${
                location.pathname === item.path
                  ? "bg-coral/10 text-coral"
                  : "text-gray-600 hover:bg-gray-100"
              }`}
            >
              {item.label}
            </Link>
          ))}
          <button
            onClick={logout}
            className="ml-2 px-4 py-2 rounded-button text-sm font-semibold text-gray-500 hover:bg-gray-100 transition-colors"
          >
            退出
          </button>
        </nav>
      </header>
      <main className="flex-1 overflow-hidden">{children}</main>
    </div>
  );
}
