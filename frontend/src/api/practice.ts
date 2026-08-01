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
