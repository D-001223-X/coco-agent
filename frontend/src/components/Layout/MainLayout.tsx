import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuthStore } from "../../store/authStore";
import { MobileBottomNav } from "./MobileBottomNav";

interface MainLayoutProps {
  children: React.ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
  const location = useLocation();
  const logout = useAuthStore((state) => state.logout);
  const user_id = useAuthStore((state) => state.user_id);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  const navItems = [
    { path: "/chat", label: "聊天" },
    { path: "/logs", label: "日志" },
  ];
  // 仅 admin 可见管理后台入口
  if (user_id === 1) {
    navItems.push({ path: "/admin", label: "管理后台" });
  }

  return (
    <div className="min-h-screen flex flex-col bg-warmwhite pb-16 md:pb-0">
      {/* 移动端：紧凑 header（仅品牌 + 管理后台入口） */}
      <header className="h-14 md:h-16 bg-white border-b border-gray-100 flex items-center justify-between px-4 md:px-6 shadow-sm">
        <Link to="/chat" className="text-lg md:text-xl font-bold text-coral">
          可可语伴
        </Link>
        {!isMobile ? (
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
        ) : (
          <Link
            to="/profile"
            className="w-9 h-9 rounded-full bg-coral/10 flex items-center justify-center text-lg"
            aria-label="我的"
          >
            👤
          </Link>
        )}
      </header>
      <main className="flex-1 overflow-hidden">{children}</main>
      {/* 移动端底部导航 */}
      {isMobile && <MobileBottomNav />}
    </div>
  );
}
