import { useNavigate } from "react-router-dom";
import { MainLayout } from "../../components/Layout/MainLayout";

export default function AssessmentPage() {
  const navigate = useNavigate();

  return (
    <MainLayout>
      <div className="max-w-2xl mx-auto px-6 py-12">
        <div className="bg-white rounded-card border border-gray-100 shadow-sm p-8 text-center">
          <h1 className="text-2xl font-bold text-gray-800 mb-2">英语水平测评</h1>
          <p className="text-sm text-gray-500 mb-8">先了解你的水平，再为你定制专属学习计划</p>

          <div className="grid grid-cols-3 gap-4 mb-8 text-left">
            <div className="bg-warmwhite rounded-lg p-4">
              <p className="text-2xl font-bold text-coral">20</p>
              <p className="text-xs text-gray-500 mt-1">听力理解</p>
            </div>
            <div className="bg-warmwhite rounded-lg p-4">
              <p className="text-2xl font-bold text-coral">15</p>
              <p className="text-xs text-gray-500 mt-1">口语表达</p>
            </div>
            <div className="bg-warmwhite rounded-lg p-4">
              <p className="text-2xl font-bold text-coral">11</p>
              <p className="text-xs text-gray-500 mt-1">阅读理解</p>
            </div>
          </div>

          <div className="text-left text-sm text-gray-600 space-y-2 mb-8">
            <p>📋 共 46 题，约需 15-20 分钟</p>
            <p>🎧 听力题请根据文字描述作答（音频版本开发中）</p>
            <p>✍️ 口语题请用英语文字输入作答</p>
            <p>📊 完成后将获得 CEFR 等级（A1-B2）与各维度得分</p>
          </div>

          <button
            onClick={() => navigate("/practice/assessment/questions")}
            className="px-8 py-3 rounded-button bg-coral hover:bg-coral-hover text-white font-semibold transition-colors"
          >
            开始测评
          </button>
        </div>
      </div>
    </MainLayout>
  );
}
