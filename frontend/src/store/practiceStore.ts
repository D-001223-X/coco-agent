import { create } from "zustand";
import {
  getAssessmentQuestions,
  submitAssessmentAnswers,
  generateLearningPlan,
} from "../api/practice";
import type {
  PracticeQuestion,
  AssessmentResult,
  LearningPlan,
  UserGoals,
} from "../api/practice";

// ── localStorage keys ────────────────────────────────────
const ASSESSMENT_KEY = "assessment";
const PLAN_KEY = "learningPlan";
const GOALS_KEY = "learningGoals";

// ── Flatten questions with their section ─────────────────
export interface FlatQuestion extends PracticeQuestion {
  section: string;
  sectionTitle: string;
}

interface PracticeState {
  questions: FlatQuestion[] | null;
  loading: boolean;
  error: string;
  currentIndex: number;
  answers: Record<string, string>;
  assessmentResult: AssessmentResult | null;
  goals: UserGoals | null;
  plan: LearningPlan | null;
  generating: boolean;
  // actions
  loadQuestions: () => Promise<void>;
  setAnswer: (id: string, value: string) => void;
  submitAssessment: () => Promise<void>;
  setGoals: (g: UserGoals) => void;
  generatePlan: (userId: string) => Promise<void>;
  reset: () => void;
}

export const usePracticeStore = create<PracticeState>((set, get) => ({
  questions: null,
  loading: false,
  error: "",
  currentIndex: 0,
  answers: {},
  assessmentResult: null,
  goals: null,
  plan: null,
  generating: false,

  loadQuestions: async () => {
    set({ loading: true, error: "" });
    try {
      const sections = await getAssessmentQuestions();
      const flattened: FlatQuestion[] = sections.flatMap((s) =>
        s.questions.map((q) => ({
          ...q,
          section: s.section,
          sectionTitle: s.title,
        }))
      );
      set({ questions: flattened, loading: false });
    } catch (e) {
      set({ loading: false, error: "题目加载失败，请稍后重试" });
    }
  },

  setAnswer: (id, value) =>
    set((state) => ({ answers: { ...state.answers, [id]: value } })),

  submitAssessment: async () => {
    set({ loading: true, error: "" });
    try {
      const result = await submitAssessmentAnswers(get().answers);
      // 持久化到 localStorage（含 cefrLevel，供 T-003 使用）
      const stored: AssessmentResult & {
        assessmentId: string;
        userId: string;
        completedAt: string;
      } = {
        ...result,
        assessmentId: `assess_${Date.now()}`,
        userId: localStorage.getItem("user_id") || "user_001",
        completedAt: new Date().toISOString(),
      };
      localStorage.setItem(ASSESSMENT_KEY, JSON.stringify(stored));
      set({ assessmentResult: result, loading: false });
    } catch (e) {
      set({ loading: false, error: "提交失败，请稍后重试" });
    }
  },

  setGoals: (g) => {
    localStorage.setItem(GOALS_KEY, JSON.stringify(g));
    set({ goals: g });
  },

  generatePlan: async (userId) => {
    set({ generating: true, error: "" });
    try {
      const assessmentRaw = localStorage.getItem(ASSESSMENT_KEY);
      if (!assessmentRaw) {
        set({ generating: false, error: "请先完成水平测评" });
        return;
      }
      const assessment = JSON.parse(assessmentRaw) as AssessmentResult;
      const goals = get().goals;
      if (!goals) {
        set({ generating: false, error: "请先填写学习目标" });
        return;
      }
      const plan = await generateLearningPlan(
        {
          cefrLevel: assessment.cefrLevel,
          listeningScore: assessment.listeningScore,
          speakingScore: assessment.speakingScore,
          readingScore: assessment.readingScore,
        },
        goals,
        userId
      );
      localStorage.setItem(PLAN_KEY, JSON.stringify(plan));
      set({ plan, generating: false });
    } catch (e) {
      set({ generating: false, error: "计划生成失败，请重试" });
    }
  },

  reset: () =>
    set({
      questions: null,
      answers: {},
      currentIndex: 0,
      assessmentResult: null,
      error: "",
    }),
}));

// ── 读取持久化数据（供页面初始化）────────────────────────
export function loadStoredAssessment(): AssessmentResult | null {
  try {
    const raw = localStorage.getItem(ASSESSMENT_KEY);
    return raw ? (JSON.parse(raw) as AssessmentResult) : null;
  } catch {
    return null;
  }
}

export function loadStoredPlan(): LearningPlan | null {
  try {
    const raw = localStorage.getItem(PLAN_KEY);
    return raw ? (JSON.parse(raw) as LearningPlan) : null;
  } catch {
    return null;
  }
}
