import type {
  Case,
  AskInput,
  CompareResponse,
  SystemStats,
  AlertItem,
  AuthUser,
  ChatSession,
  ChatMessage,
  ReviewHistoryItem,
} from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || (
  typeof window !== "undefined" && window.location.port === "8000"
    ? ""
    : "http://localhost:8000"
);

const TOKEN_KEY = "confiroute_auth_token";

export function getAuthToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setAuthToken(token: string, rememberMe = true) {
  try {
    if (rememberMe) {
      localStorage.setItem(TOKEN_KEY, token);
      sessionStorage.removeItem(TOKEN_KEY);
    } else {
      sessionStorage.setItem(TOKEN_KEY, token);
      localStorage.removeItem(TOKEN_KEY);
    }
  } catch {
    // ignore
  }
}

export function clearAuthToken() {
  try {
    localStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    // ignore
  }
}

export interface Preset {
  key: string;
  label: string;
  question: string;
  options: { A: string; B: string; C: string; D: string } | null;
  subject: string;
  sim_level?: string;
  description?: string;
}

export const PRESETS: Preset[] = [
  {
    key: "easy",
    label: "Easy factual",
    question: "Which vitamin deficiency is the specific cause of Wernicke encephalopathy?",
    options: {
      A: "Vitamin B1 (Thiamine)",
      B: "Vitamin C (Ascorbic acid)",
      C: "Vitamin D (Cholecalciferol)",
      D: "Vitamin K",
    },
    subject: "General",
    sim_level: "high",
    description: "Clear factual question with high certainty (score >= 0.80). Safely answered directly.",
  },
  {
    key: "medium",
    label: "Medium ambiguous",
    question: "A patient has chest pain, friction rub, and mild fever. What is the most likely cause?",
    options: {
      A: "Acute Pericarditis",
      B: "Aortic Dissection",
      C: "Costochondritis",
      D: "Stable Angina Pectoris",
    },
    subject: "Medicine",
    sim_level: "medium",
    description: "Moderate ambiguity (0.50 <= score < 0.80). Escalates to Tier 2 strong model for verification.",
  },
  {
    key: "highrisk",
    label: "High-risk dosage",
    question: "What is the recommended IV loading dose of Magnesium Sulfate for severe pre-eclampsia eclampsia prophylaxis?",
    options: {
      A: "4 to 6 grams IV over 15-20 minutes followed by 1-2 g/hr",
      B: "20 grams rapid IV push",
      C: "500 mg oral tablet single dose",
      D: "50 mg subcutaneous every 6 hours",
    },
    subject: "Pharmacology",
    sim_level: "high",
    description: "Contains critical medication dosage keywords. Automatic safety override directly routes to clinical review.",
  },
  {
    key: "vague",
    label: "Low confidence",
    question: "An undifferentiated metabolic acidosis presents with normal anion gap and hyperchloremia. What is the definitive proximal tubule etiology?",
    options: {
      A: "Type 1 RTA with calcium stones",
      B: "Type 2 RTA with Fanconi syndrome",
      C: "Type 4 RTA hypoaldosteronism",
      D: "Salicylate intoxication mixed disorder",
    },
    subject: "Physiology",
    sim_level: "low",
    description: "Model ambiguity and low self-consistency (< 0.50). Held for clinical review with draft answer withheld.",
  },
  {
    key: "missing",
    label: "Missing answer",
    question: "Which of the following is the primary physiological function of human erythrocytes?",
    options: {
      A: "Synthesizing clotting factors",
      B: "Digesting lipid macromolecules",
      C: "Producing myelin sheaths",
      D: "None of the above / Insufficient information",
    },
    subject: "General",
    sim_level: "low",
    description: "Correct answer ('Oxygen transport') was removed. Tests refusal safety and hallucination prevention.",
  },
];

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const fullUrl = url.startsWith("http") ? url : `${API_BASE_URL}${url}`;
  const token = getAuthToken();
  const authHeaders: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};

  const response = await fetch(fullUrl, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...authHeaders,
      ...options?.headers,
    },
  });

  if (!response.ok) {
    let errorDetail = `HTTP ${response.status}: ${response.statusText}`;
    try {
      const errJson = await response.json();
      if (errJson.detail) {
        errorDetail = typeof errJson.detail === "string" ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }

  return response.json() as Promise<T>;
}

export const api = {
  // --- Health ---
  async health(): Promise<{ status: string; app_name: string; is_mock_mode: boolean }> {
    return fetchJSON("/health");
  },

  // --- Real Authentication ---
  async login(
    email: string,
    pass: string,
    rememberMe = true
  ): Promise<{ token: string; user: AuthUser; message: string }> {
    const res = await fetchJSON<{ token: string; user: any; message: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: email.trim(),
        password: pass,
        remember_me: rememberMe,
      }),
    });
    setAuthToken(res.token, rememberMe);
    const authUser: AuthUser = {
      id: res.user.id,
      name: res.user.name,
      email: res.user.email,
      role: res.user.role,
      department: res.user.department || "Clinical Review",
      sessionStartedAt: new Date().toISOString(),
    };
    return { token: res.token, user: authUser, message: res.message };
  },

  async getMe(): Promise<AuthUser> {
    const res = await fetchJSON<{ user: any }>("/auth/me");
    return {
      id: res.user.id,
      name: res.user.name,
      email: res.user.email,
      role: res.user.role,
      department: res.user.department || "Clinical Review",
      sessionStartedAt: new Date().toISOString(),
    };
  },

  async logout(): Promise<void> {
    try {
      await fetchJSON("/auth/logout", { method: "POST" });
    } catch {
      // ignore network errors on logout
    } finally {
      clearAuthToken();
    }
  },

  async register(
    email: string,
    pass: string,
    name: string,
    role = "reviewer",
    department = "Clinical Review"
  ): Promise<{ token: string; user: AuthUser }> {
    const res = await fetchJSON<{ token: string; user: any }>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password: pass, name, role, department }),
    });
    setAuthToken(res.token, true);
    return {
      token: res.token,
      user: {
        id: res.user.id,
        name: res.user.name,
        email: res.user.email,
        role: res.user.role,
        department: res.user.department,
        sessionStartedAt: new Date().toISOString(),
      },
    };
  },

  // --- Real Inference & Routing ---
  async ask(
    question: string,
    options: AskInput["options"],
    subject: string,
    simulatedLevel?: string
  ): Promise<Case> {
    const payload = {
      question,
      options: options || undefined,
      subject: subject || "General Medicine",
      simulated_level: simulatedLevel || undefined,
      model_key: "tier1",
    };

    const resp = await fetchJSON<{
      query_id: string;
      route: string;
      status: string;
      color: string;
      final_answer: string | null;
      ai_draft_answer: string;
      scores: { s1?: number; s2?: number; s3?: number; combined?: number };
      is_high_risk: boolean;
      risk_reason: string | null;
      reason: string;
      tier_used: string;
      cost_metadata: { equivalent_cost?: number };
      tokens_used: Record<string, number>;
      case?: Case;
    }>("/ask", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    if (resp.case) {
      return resp.case;
    }

    const band = (resp.color || "green") as Case["band"];
    const route = (resp.route || "direct") as Case["route"];
    const statusVal = (resp.route === "direct" ? "answered" : "pending") as Case["status"];

    return {
      id: resp.query_id,
      ts: new Date().toISOString(),
      question,
      options: options || null,
      subject,
      tier1_answer: resp.ai_draft_answer,
      signals: {
        s1: resp.scores?.s1 ?? 0,
        s2: resp.scores?.s2 ?? 0,
        s3: resp.scores?.s3 ?? 0,
      },
      score: resp.scores?.combined ?? 0,
      risk_flag: resp.is_high_risk,
      risk_reason: resp.risk_reason,
      route,
      band,
      status: statusVal,
      tier_used: resp.tier_used === "tier2" ? 2 : 1,
      tier2_answer: resp.tier_used === "tier2" ? resp.ai_draft_answer : null,
      tier2_score: resp.tier_used === "tier2" ? (resp.scores?.combined ?? null) : null,
      final_answer: resp.final_answer,
      reason: resp.reason,
      calls: resp.tier_used === "tier2" ? 2 : 1,
      cost_equiv: resp.cost_metadata?.equivalent_cost ?? null,
      review: null,
    };
  },

  async getQueue(limit = 50): Promise<Case[]> {
    return fetchJSON<Case[]>(`/queue?limit=${limit}`);
  },

  async getCases(subject?: string, limit = 200): Promise<Case[]> {
    const params = new URLSearchParams();
    if (subject && subject !== "All") params.append("subject", subject);
    params.append("limit", String(limit));
    return fetchJSON<Case[]>(`/cases?${params.toString()}`);
  },

  async getStats(): Promise<SystemStats> {
    return fetchJSON<SystemStats>("/stats");
  },

  async getAlerts(limit = 20): Promise<AlertItem[]> {
    return fetchJSON<AlertItem[]>(`/alerts?limit=${limit}`);
  },

  async review(
    id: number | string,
    decision: "approve" | "edit" | "reject",
    editedAnswer: string | null,
    note: string,
    reviewer: string
  ): Promise<{ query_id: string; decision: string; final_answer: string | null }> {
    return fetchJSON(`/review/${encodeURIComponent(String(id))}`, {
      method: "POST",
      body: JSON.stringify({
        reviewer_name: reviewer || "Dr. Sarah Chen",
        decision,
        corrected_answer: editedAnswer || undefined,
        notes: note || undefined,
      }),
    });
  },

  async getReviewHistory(limit = 100): Promise<ReviewHistoryItem[]> {
    return fetchJSON<ReviewHistoryItem[]>(`/reviews/history?limit=${limit}`);
  },

  // --- Persistent Conversations ---
  async getConversations(limit = 50): Promise<Array<{ id: string; title: string; subject: string; updated_at: string }>> {
    return fetchJSON(`/conversations?limit=${limit}`);
  },

  async getConversation(id: string): Promise<ChatSession> {
    const conv = await fetchJSON<{
      id: string;
      title: string;
      subject: string;
      created_at: string;
      updated_at: string;
      messages: ChatMessage[];
    }>(`/conversations/${encodeURIComponent(id)}`);
    return {
      id: conv.id,
      title: conv.title,
      subject: conv.subject || "General Medicine",
      createdAt: conv.created_at || new Date().toISOString(),
      updatedAt: conv.updated_at || new Date().toISOString(),
      messages: conv.messages || [],
    };
  },

  async saveConversation(id: string, title: string, subject = "General Medicine"): Promise<void> {
    await fetchJSON("/conversations", {
      method: "POST",
      body: JSON.stringify({ id, title, subject }),
    });
  },

  async saveConversationMessage(
    conversationId: string,
    message: ChatMessage
  ): Promise<void> {
    await fetchJSON(`/conversations/${encodeURIComponent(conversationId)}/messages`, {
      method: "POST",
      body: JSON.stringify({
        id: message.id,
        role: message.role,
        content: message.content,
        options: message.options || undefined,
        subject: message.subject || undefined,
        query_id: message.caseData ? String(message.caseData.id) : undefined,
      }),
    });
  },

  async deleteConversation(id: string): Promise<void> {
    await fetchJSON(`/conversations/${encodeURIComponent(id)}`, {
      method: "DELETE",
    });
  },

  async compare(
    question: string,
    options: AskInput["options"],
    subject = "General Medicine",
    simulatedLevel?: string
  ): Promise<CompareResponse> {
    return fetchJSON<CompareResponse>("/compare", {
      method: "POST",
      body: JSON.stringify({
        question,
        options: options || undefined,
        subject,
        simulated_level: simulatedLevel || undefined,
      }),
    });
  },

  async seed(count = 20): Promise<{ message: string; count: number }> {
    return fetchJSON(`/seed?count=${count}`, {
      method: "POST",
    });
  },

  getExportCSVUrl(subject?: string): string {
    const params = subject && subject !== "All" ? `?subject=${encodeURIComponent(subject)}` : "";
    return `${API_BASE_URL}/export/csv${params}`;
  },

  // --- Admin Dashboard & Routing Logs ---
  async getAdminUsers(limit = 100): Promise<import("../types").AdminUser[]> {
    return fetchJSON(`/admin/users?limit=${limit}`);
  },

  async getAdminStats(): Promise<import("../types").AdminStats> {
    return fetchJSON("/admin/stats");
  },

  async getAdminConversations(limit = 100): Promise<import("../types").AdminConversation[]> {
    return fetchJSON(`/admin/conversations?limit=${limit}`);
  },

  async getAdminReviews(limit = 100): Promise<any[]> {
    return fetchJSON(`/admin/reviews?limit=${limit}`);
  },

  async getRoutingLogs(limit = 100, conversationId?: string): Promise<import("../types").RoutingLogItem[]> {
    const params = conversationId ? `&conversation_id=${encodeURIComponent(conversationId)}` : "";
    return fetchJSON(`/routing/logs?limit=${limit}${params}`);
  },
};

