import { useEffect, useState } from "react";
import { MainLayout } from "../../components/Layout/MainLayout";
import {
  Chart as ChartJS,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
  BarElement,
} from "chart.js";
import { Radar, Bar } from "react-chartjs-2";
import {
  fetchLearningProgress,
  generateProgressFeedback,
} from "../../api/practice";
import { loadStoredAssessment } from "../../store/practiceStore";
import type { LearningProgress } from "../../api/practice";

ChartJS.register(
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
  BarElement
);

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-white rounded-card border border-gray-100 shadow-sm p-5 text-center">
      <p className="text-3xl font-bold text-gray-800">{value}</p>
      <p className="text-xs text-gray-500 mt-1">{label}</p>
    </div>
  );
}

export default function ProgressPage() {
  const [progress, setProgress] = useState<LearningProgress | null>(null);
  const [feedback, setFeedback] = useState("");
  const [feedbackLoading, setFeedbackLoading] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const data = await fetchLearningProgress();
        setProgress(data);
      } catch (e) {
        setError("进度加载失败");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const handleGenerateFeedback = async () => {
    setFeedbackLoading(true);
    const assessment = loadStoredAssessment();
    try {
      // 后端以登录用户为准（与 GET /progress 数据源统一），前端无需传 userId
      const text = await generateProgressFeedback(
        assessment?.cefrLevel ?? "A2"
      );
      setFeedback(text);
    } catch (e) {
      setError("反馈生成失败，请重试");
    } finally {
      setFeedbackLoading(false);
    }
  };

  if (loading) {
    return (
      <MainLayout>
        <div className="flex-1 flex items-center justify-center text-gray-500">
          加载进度数据...
        </div>
      </MainLayout>
    );
  }

  // 能力雷达：听力/口语/阅读来自测评，语法/词汇来自纠错分布反推
  const assessment = loadStoredAssessment();
  const errP = progress?.errorPatterns ?? { grammar: 0, vocabulary: 0, pronunciation: 0 };
  const grammarScore = Math.max(5, 20 - (errP.grammar ?? 0) * 3);
  const vocabScore = Math.max(5, 20 - (errP.vocabulary ?? 0) * 3);

  const radarData = {
    labels: ["听力", "口语", "阅读", "语法", "词汇"],
    datasets: [
      {
        label: "当前能力",
        data: [
          assessment?.listeningScore ?? 0,
          assessment?.speakingScore ?? 0,
          assessment?.readingScore ?? 0,
          grammarScore,
          vocabScore,
        ],
        backgroundColor: "rgba(244, 114, 102, 0.2)",
        borderColor: "rgb(244, 114, 102)",
        pointBackgroundColor: "rgb(244, 114, 102)",
        borderWidth: 2,
      },
    ],
  };

  // 趋势：近 7 天活跃（从 dailyLogs 取最后 7 天）
  const last7 = (progress?.dailyLogs ?? []).slice(-7);
  const trendLabels = last7.map((d) => d.date.slice(5));
  const trendData = {
    labels: trendLabels.length ? trendLabels : ["暂无数据"],
    datasets: [
      {
        label: "对话轮次",
        data: trendLabels.length ? last7.map((d) => d.rounds) : [0],
        backgroundColor: "rgba(244, 114, 102, 0.7)",
        borderRadius: 4,
      },
    ],
  };

  const weaknessColor: Record<string, string> = {
    语法: "text-red-600",
    词汇: "text-amber-600",
    发音: "text-orange-600",
  };

  return (
    <MainLayout>
      <div className="max-w-4xl mx-auto px-6 py-10">
        <h1 className="text-2xl font-bold text-gray-800 mb-6">学习进度</h1>

        {/* 统计卡片 */}
        {/* 统计卡片：移动端横向滚动，桌面 4 列网格 */}
        <div className="flex md:grid md:grid-cols-4 gap-3 md:gap-4 mb-8 overflow-x-auto pb-1 md:overflow-visible md:pb-0 -mx-4 px-4 md:mx-0 md:px-0">
          <div className="min-w-[120px] md:min-w-0"><StatCard label="学习天数" value={progress?.totalDays ?? 0} /></div>
          <div className="min-w-[120px] md:min-w-0"><StatCard label="会话次数" value={progress?.totalSessions ?? 0} /></div>
          <div className="min-w-[120px] md:min-w-0"><StatCard label="对话轮次" value={progress?.totalRounds ?? 0} /></div>
          <div className="min-w-[120px] md:min-w-0"><StatCard label="纠正次数" value={progress?.totalCorrections ?? 0} /></div>
        </div>

        {/* 雷达图 + 趋势图 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-8">
          <div className="bg-white rounded-card border border-gray-100 shadow-sm p-6">
            <h2 className="text-base font-semibold text-gray-800 mb-4">能力雷达</h2>
            <div className="h-64 flex items-center justify-center">
              <Radar data={radarData} options={{ responsive: true, maintainAspectRatio: false }} />
            </div>
          </div>
          <div className="bg-white rounded-card border border-gray-100 shadow-sm p-6">
            <h2 className="text-base font-semibold text-gray-800 mb-2">近 7 天活跃趋势</h2>
            <p className="text-xs text-gray-400 mb-4">
              7 天活跃 {progress?.activeDays7 ?? 0} 天 · 30 天活跃 {progress?.activeDays30 ?? 0} 天
            </p>
            <div className="h-64 flex items-center justify-center">
              <Bar data={trendData} options={{ responsive: true, maintainAspectRatio: false }} />
            </div>
          </div>
        </div>

        {/* 薄弱环节 */}
        <div className="bg-white rounded-card border border-gray-100 shadow-sm p-6 mb-8">
          <h2 className="text-base font-semibold text-gray-800 mb-4">薄弱环节</h2>
          {progress && (progress.weaknesses?.length ?? 0) > 0 ? (
            <div>
              <div className="flex gap-2 mb-3 flex-wrap">
                {progress.weaknesses.map((w) => (
                  <span key={w} className={`font-semibold ${weaknessColor[w] ?? "text-red-600"}`}>
                    ● {w}
                  </span>
                ))}
              </div>
              {(progress.errorExamples?.length ?? 0) > 0 && (
                <div className="space-y-2">
                  {progress.errorExamples.slice(0, 3).map((ex, i) => (
                    <div key={i} className="bg-warmwhite rounded-lg p-3 text-xs">
                      <span className="text-gray-400 line-through">{ex.original}</span>
                      <span className="mx-1.5 text-gray-400">→</span>
                      <span className="text-gray-700 font-medium">{ex.corrected}</span>
                      <span className="ml-2 text-gray-400">（{ex.type}）</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <p className="text-gray-500 text-sm">继续练习，数据积累中...</p>
          )}
        </div>

        {/* 智能反馈 */}
        <div className="bg-coral/5 border border-coral/20 rounded-card p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-gray-800">💡 学习建议</h2>
            <button
              onClick={handleGenerateFeedback}
              disabled={feedbackLoading}
              className="px-4 py-2 rounded-button bg-coral hover:bg-coral-hover text-white text-xs font-semibold disabled:opacity-50 transition-colors"
            >
              {feedbackLoading ? "生成中..." : "生成 AI 反馈"}
            </button>
          </div>
          {feedback ? (
            <p className="text-gray-700 text-sm leading-relaxed whitespace-pre-wrap">
              {feedback}
            </p>
          ) : (
            <p className="text-gray-500 text-sm">点击按钮，AI 将根据你的学习数据生成个性化建议。</p>
          )}
        </div>

        {error && <p className="text-sm text-coral mt-4">{error}</p>}
      </div>
    </MainLayout>
  );
}
