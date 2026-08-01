import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { MainLayout } from "../../components/Layout/MainLayout";
import { GoalForm } from "../../components/Practice/GoalForm";
import { usePracticeStore } from "../../store/practiceStore";

export default function GoalsPage() {
  const navigate = useNavigate();
  const { goals, setGoals, generatePlan, plan, generating, error } = usePracticeStore();

  // 检查测评结果是否存在，不存在则跳回测评页
  useEffect(() => {
    const assessment = localStorage.getItem("assessment");
    if (!assessment) {
      navigate("/practice/assessment", { replace: true });
    }
  }, [navigate]);

  // 计划已生成 → 跳转计划展示页
  useEffect(() => {
    if (plan) {
      navigate("/practice/plan", { replace: true });
    }
  }, [plan, navigate]);

  const handleSubmit = async (g: typeof goals) => {
    if (!g) return;
    setGoals(g);
    const userId = localStorage.getItem("user_id") || "user_001";
    await generatePlan(userId);
  };

  return (
    <MainLayout>
      <div className="max-w-2xl mx-auto px-6 py-10">
        <div className="bg-white rounded-card border border-gray-100 shadow-sm p-8">
          <h1 className="text-2xl font-bold text-gray-800 mb-1">定制学习计划</h1>
          <p className="text-sm text-gray-500 mb-8">
            告诉我你的目标，AI 将为你生成专属学习路径
          </p>

          {generating ? (
            <div className="py-16 text-center">
              <div className="inline-block w-10 h-10 border-4 border-coral/30 border-t-coral rounded-full animate-spin mb-4" />
              <p className="text-gray-600">AI 正在生成你的专属学习计划...</p>
            </div>
          ) : (
            <GoalForm initial={goals} onSubmit={handleSubmit} />
          )}

          {error && <p className="mt-4 text-sm text-coral text-center">{error}</p>}
        </div>
      </div>
    </MainLayout>
  );
}
