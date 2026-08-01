import type { PracticeQuestion } from "../../api/practice";

interface QuestionCardProps {
  question: PracticeQuestion;
  value: string;
  onChange: (value: string) => void;
}

export function QuestionCard({ question, value, onChange }: QuestionCardProps) {
  return (
    <div className="bg-white rounded-card border border-gray-100 shadow-sm p-6">
      <p className="text-sm text-gray-800 leading-relaxed mb-4">{question.text}</p>

      {question.type === "multiple_choice" ? (
        <div className="space-y-2">
          {question.options.map((opt: string, i: number) => {
            const selected = value === opt;
            return (
              <button
                key={i}
                onClick={() => onChange(opt)}
                className={`w-full text-left px-4 py-3 rounded-lg border text-sm transition-colors ${
                  selected
                    ? "border-coral bg-coral/5 text-coral font-semibold"
                    : "border-gray-200 text-gray-700 hover:border-coral/40 hover:bg-warmwhite"
                }`}
              >
                {opt}
              </button>
            );
          })}
        </div>
      ) : (
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="请在此输入你的回答（英文）..."
          rows={4}
          className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-coral/30 resize-none"
        />
      )}
    </div>
  );
}
