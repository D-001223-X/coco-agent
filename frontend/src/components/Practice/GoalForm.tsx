import { useState } from "react";
import type { UserGoals } from "../../api/practice";

const GOAL_OPTIONS = ["雅思备考", "托福备考", "四六级备考", "职场提升", "日常交流", "兴趣学习"];
const LEVEL_OPTIONS = ["A1", "A2", "B1", "B2"];
const TIME_OPTIONS = [15, 30, 45, 60, 90];
const STYLE_OPTIONS = [
  { value: "visual", label: "视觉型（图文/视频）" },
  { value: "audio", label: "听觉型（听力/播客）" },
  { value: "interactive", label: "互动型（对话练习）" },
];

interface GoalFormProps {
  initial?: UserGoals | null;
  onSubmit: (goals: UserGoals) => void;
}

export function GoalForm({ initial, onSubmit }: GoalFormProps) {
  const [goal, setGoal] = useState(initial?.goal ?? "");
  const [targetLevel, setTargetLevel] = useState(initial?.targetLevel ?? "");
  const [dailyTime, setDailyTime] = useState<number>(initial?.dailyTime ?? 30);
  const [style, setStyle] = useState<string[]>(initial?.style ?? []);
  const [examDate, setExamDate] = useState(initial?.examDate ?? "");
  const [error, setError] = useState("");

  const isExamGoal = ["雅思备考", "托福备考", "四六级备考"].includes(goal);

  const toggleStyle = (v: string) => {
    setStyle((prev) =>
      prev.includes(v) ? prev.filter((s) => s !== v) : [...prev, v]
    );
  };

  const handleSubmit = () => {
    if (!goal) return setError("请选择学习目标");
    if (!targetLevel) return setError("请选择目标水平");
    if (style.length === 0) return setError("请至少选择一种学习风格");
    if (isExamGoal && !examDate) return setError("备考类目标请填写考试日期");
    setError("");
    onSubmit({ goal, targetLevel, dailyTime, style, examDate: examDate || undefined });
  };

  return (
    <div className="space-y-6">
      {/* 学习目标 */}
      <div>
        <label className="text-sm font-semibold text-gray-700 mb-2 block">学习目标</label>
        <div className="flex flex-wrap gap-2">
          {GOAL_OPTIONS.map((g) => (
            <button
              key={g}
              onClick={() => setGoal(g)}
              className={`px-4 py-2 rounded-button text-xs font-semibold transition-colors ${
                goal === g
                  ? "bg-coral text-white"
                  : "bg-white text-gray-600 border border-gray-200 hover:border-coral/40"
              }`}
            >
              {g}
            </button>
          ))}
        </div>
      </div>

      {/* 目标水平 */}
      <div>
        <label className="text-sm font-semibold text-gray-700 mb-2 block">目标水平</label>
        <div className="flex gap-2">
          {LEVEL_OPTIONS.map((lv) => (
            <button
              key={lv}
              onClick={() => setTargetLevel(lv)}
              className={`w-16 py-2 rounded-button text-sm font-bold transition-colors ${
                targetLevel === lv
                  ? "bg-coral text-white"
                  : "bg-white text-gray-600 border border-gray-200 hover:border-coral/40"
              }`}
            >
              {lv}
            </button>
          ))}
        </div>
      </div>

      {/* 每日时间 */}
      <div>
        <label className="text-sm font-semibold text-gray-700 mb-2 block">
          每日学习时间：{dailyTime} 分钟
        </label>
        <div className="flex gap-2">
          {TIME_OPTIONS.map((t) => (
            <button
              key={t}
              onClick={() => setDailyTime(t)}
              className={`px-4 py-2 rounded-button text-xs font-semibold transition-colors ${
                dailyTime === t
                  ? "bg-coral text-white"
                  : "bg-white text-gray-600 border border-gray-200 hover:border-coral/40"
              }`}
            >
              {t} 分钟
            </button>
          ))}
        </div>
      </div>

      {/* 学习风格 */}
      <div>
        <label className="text-sm font-semibold text-gray-700 mb-2 block">学习风格（可多选）</label>
        <div className="flex flex-wrap gap-2">
          {STYLE_OPTIONS.map((s) => (
            <button
              key={s.value}
              onClick={() => toggleStyle(s.value)}
              className={`px-4 py-2 rounded-button text-xs font-semibold transition-colors ${
                style.includes(s.value)
                  ? "bg-coral text-white"
                  : "bg-white text-gray-600 border border-gray-200 hover:border-coral/40"
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {/* 考试日期（备考类） */}
      {isExamGoal && (
        <div>
          <label className="text-sm font-semibold text-gray-700 mb-2 block">考试日期</label>
          <input
            type="date"
            value={examDate}
            onChange={(e) => setExamDate(e.target.value)}
            className="w-full max-w-xs px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-coral/30"
          />
        </div>
      )}

      {error && <p className="text-sm text-coral">{error}</p>}

      <button
        onClick={handleSubmit}
        className="w-full py-3 rounded-button bg-coral hover:bg-coral-hover text-white font-semibold transition-colors"
      >
        生成学习计划
      </button>
    </div>
  );
}
