import type { PracticeQuestion, PracticeSection } from "../../api/practice";

interface SectionNavProps {
  sections: PracticeSection[];
  currentSection: string;
  answers: Record<string, string>;
  onSelect: (section: string) => void;
}

export function SectionNav({ sections, currentSection, answers, onSelect }: SectionNavProps) {
  return (
    <div className="flex gap-2 flex-wrap">
      {sections.map((s) => {
        const answered = s.questions.filter((q: PracticeQuestion) => answers[q.id]?.trim()).length;
        const total = s.questions.length;
        const active = s.section === currentSection;
        return (
          <button
            key={s.section}
            onClick={() => onSelect(s.section)}
            className={`px-4 py-2 rounded-button text-xs font-semibold transition-colors ${
              active
                ? "bg-coral text-white"
                : "bg-white text-gray-600 border border-gray-200 hover:border-coral/40"
            }`}
          >
            {s.title} {answered}/{total}
          </button>
        );
      })}
    </div>
  );
}
