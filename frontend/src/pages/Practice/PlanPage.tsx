import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { MainLayout } from "../../components/Layout/MainLayout";
import { loadStoredPlan } from "../../store/practiceStore";
import type { LearningPlan } from "../../api/practice";

export default function PlanPage() {
  const navigate = useNavigate();
  const [plan, setPlan] = useState<LearningPlan | null>(null);

  useEffect(() => {
    const stored = loadStoredPlan();
    if (!stored) {
      navigate("/practice/goals", { replace: true });
      return;
    }
    setPlan(stored);
  }, [navigate]);

  if (!plan) return null;

  return (
    <MainLayout>
      <div className="max-w-3xl mx-auto px-6 py-10">
        <div className="bg-white rounded-card border border-gray-100 shadow-sm p-8">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-2xl font-bold text-gray-800">你的学习计划</h1>
            <span className="text-xs bg-green-50 text-green-700 px-3 py-1 rounded-full">
              {plan.status}
            </span>
          </div>

          <p className="text-sm text-gray-600 bg-warmwhite rounded-lg p-4 mb-6 leading-relaxed">
            {plan.overview}
          </p>

          {/* 里程碑 */}
          <h2 className="text-base font-semibold text-gray-800 mb-3">学习里程碑</h2>
          <div className="space-y-3 mb-6">
            {plan.milestones.map((m, i) => (
              <div key={m.id} className="flex gap-3 items-start">
                <div className="w-8 h-8 rounded-full bg-coral/10 text-coral flex items-center justify-center text-sm font-bold shrink-0">
                  {i + 1}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-semibold text-gray-800">{m.title}</p>
                    <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">
                      {m.weeks} 周
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">{m.description}</p>
                </div>
              </div>
            ))}
          </div>

          {/* 推荐场景 */}
          <h2 className="text-base font-semibold text-gray-800 mb-3">推荐练习场景</h2>
          <div className="flex flex-wrap gap-2 mb-8">
            {plan.recommendedScenarios.map((s, i) => (
              <span key={i} className="px-3 py-1.5 rounded-full bg-warmwhite text-xs text-gray-700 border border-gray-200">
                🎯 {s}
              </span>
            ))}
          </div>

          <button
            onClick={() => navigate("/practice/modes")}
            className="w-full py-3 rounded-button bg-coral hover:bg-coral-hover text-white font-semibold transition-colors"
          >
            开始练习 →
          </button>
        </div>
      </div>
    </MainLayout>
  );
}
