import client from "./client";

// ── Types ────────────────────────────────────────────────
export interface PracticeQuestion {
  id: string;
  type: "multiple_choice" | "text";
  text: string;
  options: string[];
}

export interface PracticeSection {
  section: string;
  title: string;
  description: string;
  questions: PracticeQuestion[];
}

export interface AssessmentResult {
  listeningScore: number;
  speakingScore: number;
  readingScore: number;
  totalScore: number;
  cefrLevel: string;
  levelDescription: string;
}

export interface Milestone {
  id: string;
  title: string;
  description: string;
  weeks: number;
  completed: boolean;
  completedAt?: string;
}

export interface LearningPlan {
  planId: string;
  userId: string;
  overview: string;
  milestones: Milestone[];
  recommendedScenarios: string[];
  status: string;
  generatedAt: string;
}

export interface UserGoals {
  goal: string;
  targetLevel: string;
  dailyTime: number;
  style: string[];
  examDate?: string;
}

interface ApiResp<T> {
  code: number;
  data: T;
  msg: string;
}

// ── Assessment API ───────────────────────────────────────
export async function getAssessmentQuestions(): Promise<PracticeSection[]> {
  const { data } = await client.get<ApiResp<{ sections: PracticeSection[] }>>(
    "/practice/assessment/questions"
  );
  return data.data.sections;
}

export async function submitAssessmentAnswers(
  answers: Record<string, string>
): Promise<AssessmentResult> {
  const { data } = await client.post<ApiResp<AssessmentResult>>(
    "/practice/assessment/submit",
    { answers }
  );
  return data.data;
}

// ── Plan API ─────────────────────────────────────────────
export async function generateLearningPlan(
  assessment: {
    cefrLevel: string;
    listeningScore: number;
    speakingScore: number;
    readingScore: number;
  },
  goals: UserGoals,
  userId: string
): Promise<LearningPlan> {
  const { data } = await client.post<ApiResp<LearningPlan>>(
    "/practice/plan/generate",
    { userId, assessment, goals }
  );
  return data.data;
}

// ── Session API (T-004) ──────────────────────────────────
export interface PracticeMode {
  id: "roleplay" | "freechat" | "topic";
  label: string;
  icon: string;
  description: string;
  scenarios: PracticeScenario[];
}

export interface PracticeScenario {
  id: string;
  name: string;
  icon: string;
  description: string;
  difficulty: "easy" | "medium" | "hard";
  tags?: string[];
  role?: string;
  category?: string;
  guidingQuestions?: string[];
  expansionQuestions?: string[];
}

export interface Correction {
  original: string;
  corrected: string;
  type: "grammar" | "vocabulary" | "pronunciation";
}

export interface ChatResponse {
  reply: string;
  correction: Correction | null;
  agentThought: string | null;
  decision: string | null;
  roundId: string;
}

export async function getPracticeModes(): Promise<PracticeMode[]> {
  const { data } = await client.get<ApiResp<{ modes: PracticeMode[] }>>(
    "/practice/modes"
  );
  return data.data.modes;
}

export async function startPracticeSession(params: {
  mode: string;
  scenario: string;
  userLevel: string;
  userId: string;
}): Promise<{ sessionId: string; agentGreeting: string }> {
  const { data } = await client.post<
    ApiResp<{ sessionId: string; agentGreeting: string }>
  >("/practice/session/start", params);
  return data.data;
}

export async function sendPracticeChat(
  sessionId: string,
  message: string
): Promise<ChatResponse> {
  const { data } = await client.post<ApiResp<ChatResponse>>(
    "/practice/session/chat",
    { sessionId, message }
  );
  return data.data;
}

export async function endPracticeSession(sessionId: string): Promise<void> {
  await client.post("/practice/session/end", { sessionId });
}

export async function switchPracticeScenario(
  sessionId: string,
  scenario: string
): Promise<{ sessionId: string; scenario: string; agentGreeting: string }> {
  const { data } = await client.post<
    ApiResp<{ sessionId: string; scenario: string; agentGreeting: string }>
  >("/practice/session/switch", { sessionId, scenario });
  return data.data;
}
