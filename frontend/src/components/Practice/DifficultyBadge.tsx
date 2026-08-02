const DIFFICULTY_META: Record<string, { label: string; color: string }> = {
  easy: { label: "简单", color: "bg-green-100 text-green-700" },
  medium: { label: "中等", color: "bg-yellow-100 text-yellow-700" },
  hard: { label: "困难", color: "bg-red-100 text-red-700" },
};

export function DifficultyBadge({ difficulty }: { difficulty: string }) {
  const meta = DIFFICULTY_META[difficulty] ?? {
    label: difficulty,
    color: "bg-gray-100 text-gray-700",
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full ${meta.color}`}>
      {meta.label}
    </span>
  );
}
