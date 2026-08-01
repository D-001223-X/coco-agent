interface QuestionProgressProps {
  current: number;
  total: number;
  answeredCount: number;
}

export function QuestionProgress({ current, total, answeredCount }: QuestionProgressProps) {
  const pct = Math.round((answeredCount / total) * 100);
  return (
    <div className="bg-white rounded-card border border-gray-100 shadow-sm p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-semibold text-gray-800">
          第 {current} / {total} 题
        </span>
        <span className="text-xs text-gray-500">已答 {answeredCount}/{total}</span>
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-coral rounded-full transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
