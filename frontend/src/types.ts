export type Band = "green" | "yellow" | "red";
export type Route = "direct" | "tier2" | "human";
export type Status = "answered" | "pending" | "resolved";

export interface Case {
  id: number | string;
  ts: string;
  question: string;
  options: { A: string; B: string; C: string; D: string } | null;
  subject: string;
  tier1_answer: string;
  signals: { s1: number; s2: number; s3: number };
  score: number;
  risk_flag: boolean;
  risk_reason: string | null;
  route: Route;
  band: Band;
  status: Status;
  tier_used: 1 | 2;
  tier2_answer: string | null;
  tier2_score: number | null;
  final_answer: string | null;
  reason: string;
  calls: number;
  cost_equiv: number | null;
  review: {
    decision: "approve" | "edit" | "reject";
    edited_answer: string | null;
    note: string;
    reviewer: string;
    ts: string;
  } | null;
}

export interface AskInput {
  question: string;
  options: { A: string; B: string; C: string; D: string } | null;
  subject: string;
  simulated_level?: string;
  provider?: string;
}

export interface CompareResponse {
  unrouted: {
    answer: string;
    letter: string;
    model: string;
    warning: string;
  };
  confiroute: Case;
}

export interface SystemStats {
  total_queries: number;
  routes: {
    direct: number;
    tier2: number;
    human: number;
  };
  reviews: {
    pending: number;
    approved: number;
    edited: number;
    rejected: number;
  };
}

export interface AlertItem {
  id?: number;
  alert_type: string;
  message: string;
  severity: string;
  created_at?: string;
}

/* Chat & Session Types */
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  options?: { A: string; B: string; C: string; D: string } | null;
  subject?: string;
  caseData?: Case;
  isTyping?: boolean;
  error?: string | null;
}

export interface ChatSession {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  subject: string;
  messages: ChatMessage[];
  lastCase?: Case;
}

/* Authentication Types */
export interface AuthUser {
  id: string;
  name: string;
  email: string;
  role: string;
  department: string;
  avatarUrl?: string;
  sessionStartedAt: string;
}

/* Navigation views */
export type ViewMode = "chat" | "queue" | "compare" | "analytics";
