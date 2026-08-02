import { NavLink } from "react-router-dom";

const TABS = [
  { path: "/practice/assessment", icon: "🏠", label: "首页" },
  { path: "/practice/modes", icon: "💬", label: "陪练" },
  { path: "/practice/progress", icon: "📊", label: "进度" },
  { path: "/chat", icon: "💡", label: "客服" },
  { path: "/profile", icon: "👤", label: "我的" },
];

export function MobileBottomNav() {
  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 flex items-center justify-around h-16 px-2 z-50 safe-area-pb md:hidden">
      {TABS.map((tab) => (
        <NavLink
          key={tab.path}
          to={tab.path}
          end={tab.path === "/chat"}
          className={({ isActive }) =>
            `relative flex flex-col items-center justify-center gap-0.5 py-1 px-3 min-w-[44px] min-h-[44px] transition-colors ${
              isActive ? "text-[#FF6B6B]" : "text-gray-400"
            }`
          }
        >
          {({ isActive }) => (
            <>
              <span className="text-xl leading-none">{tab.icon}</span>
              <span className="text-[10px] font-medium">{tab.label}</span>
              {/* 激活下划线标识 */}
              <span
                className={`absolute top-0 w-6 h-0.5 rounded-full transition-opacity ${
                  isActive ? "bg-[#FF6B6B] opacity-100" : "opacity-0"
                }`}
              />
            </>
          )}
        </NavLink>
      ))}
    </nav>
  );
}
