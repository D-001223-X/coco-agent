import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { MainLayout } from "../../components/Layout/MainLayout";
import { ModeCard } from "../../components/Practice/ModeCard";
import { usePracticeStore } from "../../store/practiceStore";
import { loadStoredAssessment, loadStoredPlan } from "../../store/practiceStore";
import type { PracticeMode } from "../../api/practice";

export default function PracticeModesPage() {
  const navigate = useNavigate();
  const { modes, loadModes, startSession, error } = usePracticeStore();
  const [selectedMode, setSelectedMode] = useState<PracticeMode | null>(null);
  const [scenario, setScenario] = useState("");
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    // 前置检查：必须已测评 + 已生成计划
    if (!loadStoredAssessment() || !loadStoredPlan()) {
      navigate("/practice/plan", { replace: true });
      return;
    }
    if (modes.length === 0) loadModes();
  }, [navigate, modes.length, loadModes]);

  const handleModeSelect = (mode: PracticeMode) => {
    setSelectedMode(mode);
    setScenario(mode.scenarios[0] ?? "");
  };

  const handleStart = async () => {
    if (!selectedMode || starting) return;
    setStarting(true);
    const assessment = loadStoredAssessment();
    const userId = localStorage.getItem("user_id") || "user_001";
    const sessionId = await startSession(
      selectedMode.id,
      scenario,
      assessment?.cefrLevel ?? "A2",
      userId
    );
    setStarting(false);
    if (sessionId) {
      navigate("/practice/chat");
    }
  };

  return (
    <MainLayout>
      <div className="max-w-4xl mx-auto px-6 py-10">
        <h1 className="text-2xl font-bold text-gray-800 text-center mb-2">选择陪练模式</h1>
        <p className="text-sm text-gray-500 text-center mb-8">三种模式，随时开练</p>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
          {modes.map((mode) => (
            <ModeCard
              key={mode.id}
              mode={mode}
              selected={selectedMode?.id === mode.id}
              onClick={() => handleModeSelect(mode)}
            />
          ))}
        </div>

        {selectedMode && (
          <div className="bg-white rounded-card border border-gray-100 shadow-sm p-6 max-w-md mx-auto">
            <p className="text-sm font-semibold text-gray-700 mb-3">选择场景 / 话题</p>
            <div className="flex flex-wrap gap-2 mb-6">
              {selectedMode.scenarios.map((s) => (
                <button
                  key={s}
                  onClick={() => setScenario(s)}
                  className={`px-3 py-1.5 rounded-button text-xs font-semibold transition-colors ${
                    scenario === s
                      ? "bg-coral text-white"
                      : "bg-warmwhite text-gray-600 border border-gray-200 hover:border-coral/40"
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>
            <button
              onClick={handleStart}
              disabled={starting}
              className="w-full py-3 rounded-button bg-coral hover:bg-coral-hover text-white font-semibold disabled:opacity-50 transition-colors"
            >
              {starting ? "启动中..." : "开始练习"}
            </button>
          </div>
        )}

        {error && <p className="text-center text-sm text-coral mt-4">{error}</p>}
      </div>
    </MainLayout>
  );
}
