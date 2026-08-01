import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { MainLayout } from "../../components/Layout/MainLayout";
import { loadStoredAssessment } from "../../store/practiceStore";
import type { AssessmentResult } from "../../api/practice";

export default function AssessmentResultPage() {
  const navigate = useNavigate();
  const [result, setResult] = useState<AssessmentResult | null>(null);

  useEffect(() => {
    const stored = loadStoredAssessment();
    if (!stored) {
      navigate("/practice/assessment", { replace: true });
      return;
    }
    setResult(stored);
  }, [navigate]);

  if (!result) return null;

  const scores = [
    { label: "听力理解", score: result.listeningScore, max: 20 },
    { label: "口语表达", score: result.speakingScore, max: 15 },
    { label: "阅读理解", score: result.readingScore, max: 11 },
  ];

  return (
    <MainLayout>
      <div className="max-w-2xl mx-auto px-6 py-12">
        <div className="bg-white rounded-card border border-gray-100 shadow-sm p-8 text-center">
          <h1 className="text-2xl font-bold text-gray-800 mb-2">测评完成 🎉</h1>

          <div className="my-8">
            <p className="text-sm text-gray-500 mb-1">你的 CEFR 等级</p>
            <div className="text-6xl font-bold text-coral">{result.cefrLevel}</div>
            <p className="text-sm text-gray-600 mt-3">{result.levelDescription}</p>
          </div>

          <div className="grid grid-cols-3 gap-4 mb-8">
            {scores.map((s) => (
              <div key={s.label} className="bg-warmwhite rounded-lg p-4">
                <p className="text-2xl font-bold text-gray-800">
                  {s.score}
                  <span className="text-sm text-gray-400">/{s.max}</span>
                </p>
                <p className="text-xs text-gray-500 mt-1">{s.label}</p>
              </div>
            ))}
          </div>

          <p className="text-sm text-gray-600 mb-8">
            总分 {result.totalScore}/46 · 结果已保存，接下来为你生成个性化学习计划
          </p>

          <button
            onClick={() => navigate("/practice/goals")}
            className="px-8 py-3 rounded-button bg-coral hover:bg-coral-hover text-white font-semibold transition-colors"
          >
            下一步：定制学习计划 →
          </button>
        </div>
      </div>
    </MainLayout>
  );
}
