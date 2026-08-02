import type { Correction } from "../../api/practice";

const TYPE_LABEL: Record<string, string> = {
  grammar: "语法",
  vocabulary: "词汇",
  pronunciation: "发音",
};

const TYPE_COLOR: Record<string, string> = {
  grammar: "bg-amber-50 text-amber-700",
  vocabulary: "bg-blue-50 text-blue-700",
  pronunciation: "bg-green-50 text-green-700",
};

export function CorrectionDisplay({ correction }: { correction: Correction }) {
  const color = TYPE_COLOR[correction.type] ?? "bg-gray-100 text-gray-700";
  return (
    <div className="bg-warmwhite border border-gray-100 rounded-lg p-2.5 text-xs">
      <div className="flex items-center gap-2 mb-1.5">
        <span className={`px-1.5 py-0.5 rounded ${color} font-semibold`}>
          {TYPE_LABEL[correction.type] ?? correction.type}
        </span>
        <span className="text-gray-400">纠错建议</span>
      </div>
      <p className="text-gray-500">
        <span className="line-through text-gray-400">{correction.original}</span>
        <span className="mx-1.5 text-gray-400">→</span>
        <span className="font-semibold text-gray-700">{correction.corrected}</span>
      </p>
    </div>
  );
}
