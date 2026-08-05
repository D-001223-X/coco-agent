import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { MainLayout } from "../components/Layout/MainLayout";
import { isAdminUser, useAuthStore } from "../store/authStore";
import { loadStoredAssessment } from "../store/practiceStore";

export default function ProfilePage() {
  const user_id = useAuthStore((state) => state.user_id);
  const email = useAuthStore((state) => state.email);
  const logout = useAuthStore((state) => state.logout);
  const assessment = loadStoredAssessment();
  const isGuest = !user_id;

  // R-001 隐藏管理员登录入口：连击 5 次跳转 /login
  const [clickCount, setClickCount] = useState(0);
  const clickTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleSecretClick = () => {
    setClickCount((prev) => {
      const newCount = prev + 1;
      if (newCount >= 5) {
        if (clickTimer.current) clearTimeout(clickTimer.current);
        window.location.href = "/login";
        return 0;
      }
      if (clickTimer.current) clearTimeout(clickTimer.current);
      clickTimer.current = setTimeout(() => setClickCount(0), 500);
      return newCount;
    });
  };
  // 进度提示：连击时在隐藏区右侧显示圆点（点击后立即清除）
  const secretProgress = clickCount > 0 ? "·".repeat(clickCount) : "";

  const cefrLabel: Record<string, string> = {
    A1: "入门级",
    A2: "基础级",
    B1: "进阶级",
    B2: "中高级",
  };

  return (
    <MainLayout>
      <div className="max-w-md mx-auto px-4 py-8">
        <div className="flex items-center mb-6">
          <h1 className="text-xl font-bold text-gray-800">我的</h1>
          {/* R-001 隐蔽点击区：连击 5 次跳登录 */}
          <span
            className="inline-block w-8 h-8 cursor-pointer opacity-0 select-none"
            onClick={handleSecretClick}
            aria-hidden="true"
          />
          {secretProgress && (
            <span className="text-coral text-xs font-bold">{secretProgress}</span>
          )}
        </div>

        {/* 用户卡片 */}
        <div className="bg-white rounded-card border border-gray-100 shadow-sm p-6 mb-6">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-full bg-coral/10 flex items-center justify-center text-2xl">
              {isGuest ? "👤" : "🎓"}
            </div>
            <div>
              <p className="font-semibold text-gray-800">
                {isGuest ? "访客用户" : `用户 #${user_id}`}
              </p>
              <p className="text-xs text-gray-500 mt-0.5">
                {isGuest
                  ? "扫码体验模式 · 数据保存在本机"
                  : `已登录 · ${email ?? ""}`}
              </p>
              {isAdminUser(user_id) && (
                <p className="text-green-600 text-xs font-medium mt-1">
                  👤 管理员
                </p>
              )}
            </div>
          </div>
        </div>

        {/* 测评结果 */}
        {assessment && (
          <div className="bg-white rounded-card border border-gray-100 shadow-sm p-6 mb-6">
            <p className="text-xs text-gray-400 mb-3">我的英语水平</p>
            <div className="flex items-center gap-3">
              <span className="text-4xl font-bold text-coral">
                {assessment.cefrLevel}
              </span>
              <div className="text-sm text-gray-600">
                <p>{cefrLabel[assessment.cefrLevel] ?? "未分级"}</p>
                <p className="text-xs text-gray-400 mt-0.5">
                  听 {assessment.listeningScore} · 说 {assessment.speakingScore} · 读{" "}
                  {assessment.readingScore}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* 快捷入口 */}
        <div className="space-y-3">
          <Link
            to="/practice/assessment"
            className="block bg-white rounded-card border border-gray-100 shadow-sm p-4 text-sm text-gray-700 hover:border-coral/40 transition-colors"
          >
            📝 重新测评
          </Link>
          <Link
            to="/practice/modes"
            className="block bg-white rounded-card border border-gray-100 shadow-sm p-4 text-sm text-gray-700 hover:border-coral/40 transition-colors"
          >
            💬 开始陪练
          </Link>
          <Link
            to="/chat"
            className="block bg-white rounded-card border border-gray-100 shadow-sm p-4 text-sm text-gray-700 hover:border-coral/40 transition-colors"
          >
            💡 联系客服
          </Link>
          {isAdminUser(user_id) && (
            <Link
              to="/admin"
              className="block bg-white rounded-card border border-gray-100 shadow-sm p-4 text-sm text-gray-700 hover:border-coral/40 transition-colors"
            >
              ⚙️ 管理后台
            </Link>
          )}
          {!isGuest && (
            <button
              onClick={logout}
              className="w-full text-left bg-white rounded-card border border-gray-200 shadow-sm p-4 text-sm text-red-500 transition-colors"
            >
              退出登录
            </button>
          )}
        </div>
      </div>
    </MainLayout>
  );
}
