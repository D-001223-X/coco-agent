import { create } from "zustand";
import { useAuthStore } from "./authStore";
import {
  getAssessmentQuestions,
  submitAssessmentAnswers,
  generateLearningPlan,
  getPracticeModes,
  startPracticeSession,
  sendPracticeChat,
  endPracticeSession,
  switchPracticeScenario,
} from "../api/practice";
import type {
  PracticeQuestion,
  AssessmentResult,
  LearningPlan,
  UserGoals,
  PracticeMode,
  Correction,
  ReactLoopStep,
} from "../api/practice";

// ── localStorage keys ────────────────────────────────────
const ASSESSMENT_KEY = "assessment";
const PLAN_KEY = "learningPlan";
const GOALS_KEY = "learningGoals";
const SESSION_KEY = "practiceSession";

import { getDeviceId as getGlobalDeviceId } from "../utils/deviceId";

// 统一取用户标识：已登录 → 用户 ID；访客 → 设备 ID（进度/反馈按此隔离）
// P2 修复：访客统一用全局 device_id（utils/deviceId，与 X-Device-ID 头一致），
// 保证会话记录归属与进度查询使用同一个设备标识。
export function currentUserId(): string {
  const uid = useAuthStore.getState().user_id;
  return uid != null ? String(uid) : getGlobalDeviceId();
}

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
  // ── 会话状态（T-004）──
  modes: PracticeMode[];
  sessionId: string | null;
  currentModeId: string | null;
  currentScenario: string | null;
  chatMessages: ChatMessage[];
  chatting: boolean;
  // actions
  loadQuestions: () => Promise<void>;
  setAnswer: (id: string, value: string) => void;
  submitAssessment: () => Promise<void>;
  setGoals: (g: UserGoals) => void;
  generatePlan: (userId: string) => Promise<void>;
  loadModes: () => Promise<void>;
  startSession: (mode: string, scenario: string, userLevel: string, userId: string) => Promise<string | null>;
  sendChat: (message: string) => Promise<void>;
  switchScenario: (scenario: string) => Promise<void>;
  endSession: () => Promise<void>;
  reset: () => void;
}

export interface ChatMessage {
  id: string;
  role: "user" | "agent";
  content: string;
  correction?: Correction | null;
  agentThought?: string | null;
  reactLoop?: ReactLoopStep[];
  naturalSummary?: string;
  timestamp: string;
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
  modes: [],
  sessionId: null,
  currentModeId: null,
  currentScenario: null,
  chatMessages: [],
  chatting: false,

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
        userId: currentUserId(),
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

  // ── 会话 actions（T-004）──────────────────────────────
  loadModes: async () => {
    try {
      const modes = await getPracticeModes();
      set({ modes });
    } catch (e) {
      set({ error: "模式加载失败" });
    }
  },

  startSession: async (mode, scenario, userLevel, _userId) => {
    set({ chatting: true, error: "" });
    try {
      const { sessionId, agentGreeting } = await startPracticeSession({
        mode,
        scenario,
        userLevel,
        userId: currentUserId(), // 统一用登录用户 ID（与进度统计口径一致）
      });
      const greeting: ChatMessage = {
        id: `round_${Date.now()}`,
        role: "agent",
        content: agentGreeting,
        correction: null,
        agentThought: null,
        timestamp: new Date().toISOString(),
      };
      localStorage.setItem(SESSION_KEY, sessionId);
      set({
        sessionId,
        currentModeId: mode,
        currentScenario: scenario,
        chatMessages: [greeting],
        chatting: false,
      });
      return sessionId;
    } catch (e) {
      set({ chatting: false, error: "会话启动失败，请重试" });
      return null;
    }
  },

  sendChat: async (message) => {
    const sessionId = get().sessionId;
    if (!sessionId) {
      set({ error: "会话未启动" });
      return;
    }
    const userMsg: ChatMessage = {
      id: `round_${Date.now()}`,
      role: "user",
      content: message,
      timestamp: new Date().toISOString(),
    };
    set((state) => ({
      chatting: true,
      error: "",
      chatMessages: [...state.chatMessages, userMsg],
    }));
    try {
      const res = await sendPracticeChat(sessionId, message);
      const agentMsg: ChatMessage = {
        id: res.roundId,
        role: "agent",
        content: res.reply,
        correction: res.correction,
        agentThought: res.agentThought,
        reactLoop: res.react_loop,
        naturalSummary: res.naturalSummary,
        timestamp: new Date().toISOString(),
      };
      set((state) => ({
        chatting: false,
        chatMessages: [...state.chatMessages, agentMsg],
      }));
    } catch (e) {
      set({ chatting: false, error: "回复失败，请重试" });
    }
  },

  switchScenario: async (scenario) => {
    const sessionId = get().sessionId;
    if (!sessionId) {
      set({ error: "会话未启动" });
      return;
    }
    set({ chatting: true, error: "" });
    try {
      const res = await switchPracticeScenario(sessionId, scenario);
      const switchMsg: ChatMessage = {
        id: `round_${Date.now()}`,
        role: "agent",
        content: res.agentGreeting,
        correction: null,
        agentThought: "场景/话题动态切换，历史上下文已保留",
        timestamp: new Date().toISOString(),
      };
      set((state) => ({
        chatting: false,
        currentScenario: res.scenario,
        chatMessages: [...state.chatMessages, switchMsg],
      }));
    } catch (e) {
      set({ chatting: false, error: "场景切换失败，请重试" });
    }
  },

  endSession: async () => {
    const sessionId = get().sessionId;
    if (sessionId) {
      try {
        await endPracticeSession(sessionId);
      } catch (e) {
        // 忽略结束失败
      }
    }
    localStorage.removeItem(SESSION_KEY);
    set({ sessionId: null, chatMessages: [] });
  },
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
