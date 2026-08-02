import type { PracticeMode } from "../../api/practice";

interface ModeCardProps {
  mode: PracticeMode;
  selected: boolean;
  onClick: () => void;
}

export function ModeCard({ mode, selected, onClick }: ModeCardProps) {
  return (
    <button
      onClick={onClick}
      className={`rounded-card border p-5 text-center transition-all ${
        selected
          ? "border-coral bg-coral/5 shadow-md"
          : "border-gray-200 bg-white hover:border-coral/40 hover:shadow-sm"
      }`}
    >
      <div className="text-4xl mb-2">{mode.icon}</div>
      <p className="font-semibold text-gray-800 mb-1">{mode.label}</p>
      <p className="text-xs text-gray-500 leading-relaxed">{mode.description}</p>
    </button>
  );
}
