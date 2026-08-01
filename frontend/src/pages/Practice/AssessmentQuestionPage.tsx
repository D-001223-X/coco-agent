import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { MainLayout } from "../../components/Layout/MainLayout";
import { QuestionCard } from "../../components/Practice/QuestionCard";
import { QuestionProgress } from "../../components/Practice/QuestionProgress";
import { SectionNav } from "../../components/Practice/SectionNav";
import { usePracticeStore } from "../../store/practiceStore";

export default function AssessmentQuestionPage() {
  const navigate = useNavigate();
  const {
    questions,
    answers,
    setAnswer,
    submitAssessment,
    loadQuestions,
    loading,
    error,
  } = usePracticeStore();

  const [currentSection, setCurrentSection] = useState("listening");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!questions) loadQuestions();
  }, [questions, loadQuestions]);

  const currentQuestions = useMemo(
    () => (questions ?? []).filter((q) => q.section === currentSection),
    [questions, currentSection]
  );

  const answeredCount = useMemo(
    () => Object.values(answers).filter((v) => v?.trim()).length,
    [answers]
  );

  if (loading && !questions) {
    return (
      <MainLayout>
        <div className="flex-1 flex items-center justify-center text-gray-500">
          正在加载题目...
        </div>
      </MainLayout>
    );
  }

  if (error && !questions) {
    return (
      <MainLayout>
        <div className="flex-1 flex flex-col items-center justify-center gap-4">
          <p className="text-coral">{error}</p>
          <button
            onClick={loadQuestions}
            className="px-6 py-2 rounded-button bg-coral text-white text-sm"
          >
            重试
          </button>
        </div>
      </MainLayout>
    );
  }

  const handleSubmit = async () => {
    if (window.confirm(`已答 ${answeredCount}/46 题，确定提交测评吗？`)) {
      setSubmitting(true);
      await submitAssessment();
      if (!usePracticeStore.getState().error) {
        navigate("/practice/assessment/result");
      }
      setSubmitting(false);
    }
  };

  return (
    <MainLayout>
      <div className="max-w-3xl mx-auto px-6 py-6 space-y-4 w-full">
        <SectionNav
          sections={
            questions
              ? [...new Set(questions.map((q) => q.section))].map((sec) => ({
                  section: sec,
                  title: questions.find((q) => q.section === sec)?.sectionTitle ?? sec,
                  description: "",
                  questions: questions.filter((q) => q.section === sec),
                }))
              : []
          }
          currentSection={currentSection}
          answers={answers}
          onSelect={setCurrentSection}
        />

        <QuestionProgress
          current={currentQuestions.length ? 1 : 0}
          total={questions?.length ?? 46}
          answeredCount={answeredCount}
        />

        <div className="space-y-3">
          {currentQuestions.map((q) => (
            <QuestionCard
              key={q.id}
              question={q}
              value={answers[q.id] ?? ""}
              onChange={(v) => setAnswer(q.id, v)}
            />
          ))}
        </div>

        <div className="flex items-center justify-between pt-4 pb-8">
          <button
            onClick={() => {
              const order = ["listening", "speaking", "reading"];
              const idx = order.indexOf(currentSection);
              if (idx > 0) setCurrentSection(order[idx - 1]);
            }}
            disabled={currentSection === "listening"}
            className="px-5 py-2.5 rounded-button text-sm font-semibold text-gray-600 border border-gray-200 hover:bg-gray-50 disabled:opacity-40"
          >
            上一部分
          </button>
          <button
            onClick={() => {
              const order = ["listening", "speaking", "reading"];
              const idx = order.indexOf(currentSection);
              if (idx < order.length - 1) setCurrentSection(order[idx + 1]);
            }}
            className="px-5 py-2.5 rounded-button text-sm font-semibold text-gray-600 border border-gray-200 hover:bg-gray-50"
          >
            下一部分
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="px-6 py-2.5 rounded-button bg-coral hover:bg-coral-hover text-white text-sm font-semibold disabled:opacity-50"
          >
            {submitting ? "提交中..." : "提交测评"}
          </button>
        </div>
      </div>
    </MainLayout>
  );
}
