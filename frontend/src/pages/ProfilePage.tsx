import { Link } from "react-router-dom";
import { MainLayout } from "../components/Layout/MainLayout";
import { useAuthStore } from "../store/authStore";
import { loadStoredAssessment } from "../store/practiceStore";

export default function ProfilePage() {
  const user_id = useAuthStore((state) => state.user_id);
  const logout = useAuthStore((state) => state.logout);
  const assessment = loadStoredAssessment();
  const isGuest = !user_id;

  const cefrLabel: Record<string, string> = {
    A1: "入门级",
    A2: "基础级",
    B1: "进阶级",
    B2: "中高级",
  };

  return (
    <MainLayout>
      <div className="max-w-md mx-auto px-4 py-8">
        <h1 className="text-xl font-bold text-gray-800 mb-6">我的</h1>

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
                  : "已登录 · 数据云端同步"}
              </p>
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
          {user_id === 1 && (
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
