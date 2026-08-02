import { useState } from "react";

export function AgentThoughtDisplay({ thought }: { thought: string }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="border-t border-gray-100 pt-2 mt-1">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="text-[11px] text-gray-400 hover:text-coral transition-colors"
      >
        {expanded ? "▲ Agent 思考" : "▼ Agent 思考"}
      </button>
      {expanded && (
        <p className="mt-1 text-[11px] text-gray-400 leading-relaxed">{thought}</p>
      )}
    </div>
  );
}
