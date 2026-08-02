import type { PracticeScenario } from "../../api/practice";
import { DifficultyBadge } from "./DifficultyBadge";

interface ScenarioSelectorProps {
  scenarios: PracticeScenario[];
  selectedId: string;
  onSelect: (id: string) => void;
}

export function ScenarioSelector({
  scenarios,
  selectedId,
  onSelect,
}: ScenarioSelectorProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
      {scenarios.map((s) => {
        const selected = selectedId === s.id;
        return (
          <div
            key={s.id}
            onClick={() => onSelect(s.id)}
            className={`p-4 border-2 rounded-lg cursor-pointer transition-all ${
              selected
                ? "border-coral bg-coral/5 shadow-sm"
                : "border-gray-200 hover:border-coral/40"
            }`}
          >
            <div className="flex items-start gap-2">
              <span className="text-2xl">{s.icon}</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium text-gray-800 truncate">{s.name}</span>
                  <DifficultyBadge difficulty={s.difficulty} />
                </div>
                <p className="text-sm text-gray-500 mt-0.5 line-clamp-1">
                  {s.description}
                </p>
                {(s.tags?.length ?? 0) > 0 && (
                  <div className="flex gap-1 mt-1.5 flex-wrap">
                    {s.tags!.map((tag) => (
                      <span
                        key={tag}
                        className="text-[11px] bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
