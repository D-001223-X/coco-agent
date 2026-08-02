import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { MainLayout } from "../../components/Layout/MainLayout";
import { ModeCard } from "../../components/Practice/ModeCard";
import { ScenarioSelector } from "../../components/Practice/ScenarioSelector";
import { usePracticeStore } from "../../store/practiceStore";
import { loadStoredAssessment, loadStoredPlan } from "../../store/practiceStore";
import type { PracticeMode, PracticeScenario } from "../../api/practice";

export default function PracticeModesPage() {
  const navigate = useNavigate();
  const { modes, loadModes, startSession, error } = usePracticeStore();
  const [selectedMode, setSelectedMode] = useState<PracticeMode | null>(null);
  const [scenarioId, setScenarioId] = useState("");
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
    setScenarioId(mode.scenarios[0]?.id ?? "");
  };

  const handleStart = async () => {
    if (!selectedMode || starting) return;
    setStarting(true);
    const assessment = loadStoredAssessment();
    const userId = localStorage.getItem("user_id") || "user_001";
    const sessionId = await startSession(
      selectedMode.id,
      scenarioId,
      assessment?.cefrLevel ?? "A2",
      userId
    );
    setStarting(false);
    if (sessionId) {
      navigate("/practice/chat");
    }
  };

  const selectedScenario: PracticeScenario | undefined = selectedMode?.scenarios.find(
    (s) => s.id === scenarioId
  );

  return (
    <MainLayout>
      <div className="max-w-4xl mx-auto px-6 py-10">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-800">选择陪练模式</h1>
            <p className="text-sm text-gray-500 mt-1">三种模式，随时开练</p>
          </div>
          <button
            onClick={() => navigate("/practice/progress")}
            className="px-4 py-2 rounded-button text-xs font-semibold text-gray-600 border border-gray-200 hover:text-coral hover:border-coral/40 transition-colors"
          >
            📊 学习进度
          </button>
        </div>

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
          <div className="bg-white rounded-card border border-gray-100 shadow-sm p-6">
            <p className="text-sm font-semibold text-gray-700 mb-3">
              选择场景 / 话题（{selectedMode.scenarios.length} 个）
            </p>
            <ScenarioSelector
              scenarios={selectedMode.scenarios}
              selectedId={scenarioId}
              onSelect={setScenarioId}
            />
            <div className="mt-6 flex items-center justify-between">
              {selectedScenario && (
                <p className="text-xs text-gray-500">
                  {selectedScenario.role ? `Agent 扮演：${selectedScenario.role}` : ""}
                  {selectedScenario.guidingQuestions
                    ? ` · ${selectedScenario.guidingQuestions.length} 个引导问题`
                    : ""}
                  {selectedScenario.expansionQuestions
                    ? ` · ${selectedScenario.expansionQuestions.length} 个展开问题`
                    : ""}
                </p>
              )}
              <button
                onClick={handleStart}
                disabled={starting || !scenarioId}
                className="ml-auto px-8 py-3 rounded-button bg-coral hover:bg-coral-hover text-white font-semibold disabled:opacity-50 transition-colors"
              >
                {starting ? "启动中..." : "开始练习"}
              </button>
            </div>
          </div>
        )}

        {error && <p className="text-center text-sm text-coral mt-4">{error}</p>}
      </div>
    </MainLayout>
  );
}
