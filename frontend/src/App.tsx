import React, { useState, useEffect, useCallback } from "react";
import { AuthProvider, useAuth } from "./context/AuthContext";
import LoginPage from "./pages/LoginPage";
import ChatWorkspace from "./pages/ChatWorkspace";
import ReviewQueueView from "./pages/ReviewQueueView";
import SideBySideView from "./pages/SideBySideView";
import AnalyticsView from "./pages/AnalyticsView";
import AppSidebar from "./components/AppSidebar";
import ReviewModal from "./components/ReviewModal";
import SettingsModal from "./components/SettingsModal";
import ProfileModal from "./components/ProfileModal";
import type { Case, ChatSession, ChatMessage, ViewMode } from "./types";
import { api, type Preset } from "./lib/api";

const SESSIONS_STORAGE_KEY = "confiroute_chat_sessions_v2";

function MainApp() {
  const { user, isAuthenticated, isLoading } = useAuth();

  // Navigation & Modal States
  const [currentView, setCurrentView] = useState<ViewMode>("chat");
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  const [reviewingCase, setReviewingCase] = useState<Case | null>(null);

  // Clinician auditor name
  const [reviewerName, setReviewerName] = useState(user?.name || "Dr. Sarah Chen");

  // Cases loaded from backend
  const [cases, setCases] = useState<Case[]>([]);
  const [pending, setPending] = useState(false);

  // Chat sessions state
  const [sessions, setSessions] = useState<ChatSession[]>(() => {
    try {
      const stored = localStorage.getItem(SESSIONS_STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      }
    } catch (e) {
      console.warn("Could not load sessions from localStorage:", e);
    }
    // Default initial session
    const initialSessionId = `sess_${Date.now()}`;
    return [
      {
        id: initialSessionId,
        title: "Clinical Consultation",
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        subject: "General Medicine",
        messages: [],
      },
    ];
  });

  const [currentSessionId, setCurrentSessionId] = useState<string>(sessions[0]?.id || "");

  // Sync sessions to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(SESSIONS_STORAGE_KEY, JSON.stringify(sessions));
    } catch {
      // ignore
    }
  }, [sessions]);

  // Load existing cases from backend SQLite
  const reloadCases = useCallback(async () => {
    try {
      const serverCases = await api.getCases();
      setCases(serverCases);
    } catch (err) {
      console.warn("Could not connect to FastAPI backend:", err);
    }
  }, []);

  useEffect(() => {
    if (isAuthenticated) {
      reloadCases();
    }
  }, [isAuthenticated, reloadCases]);

  // Active session helper
  const currentSession =
    sessions.find((s) => s.id === currentSessionId) ||
    sessions[0] || {
      id: "fallback",
      title: "Clinical Consultation",
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      subject: "General Medicine",
      messages: [],
    };

  // Create new session
  const handleNewSession = () => {
    const newId = `sess_${Date.now()}`;
    const newSession: ChatSession = {
      id: newId,
      title: "New Clinical Inquiry",
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      subject: "General Medicine",
      messages: [],
    };
    setSessions((prev) => [newSession, ...prev]);
    setCurrentSessionId(newId);
  };

  // Delete session
  const handleDeleteSession = (id: string) => {
    setSessions((prev) => {
      const next = prev.filter((s) => s.id !== id);
      if (next.length === 0) {
        const replacement: ChatSession = {
          id: `sess_${Date.now()}`,
          title: "New Clinical Inquiry",
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          subject: "General Medicine",
          messages: [],
        };
        setCurrentSessionId(replacement.id);
        return [replacement];
      }
      if (currentSessionId === id) {
        setCurrentSessionId(next[0].id);
      }
      return next;
    });
  };

  // Clear current session messages
  const handleClearSession = () => {
    setSessions((prev) =>
      prev.map((s) =>
        s.id === currentSession.id
          ? { ...s, messages: [], updatedAt: new Date().toISOString() }
          : s
      )
    );
  };

  // Send message and trigger ConfiRoute confidence routing
  const handleSendMessage = async (
    question: string,
    options: { A: string; B: string; C: string; D: string } | null,
    subject: string,
    simulatedLevel?: string
  ) => {
    const userMsgId = `msg_user_${Date.now()}`;
    const userMessage: ChatMessage = {
      id: userMsgId,
      role: "user",
      content: question,
      timestamp: new Date().toISOString(),
      options,
      subject,
    };

    // Add user message immediately
    setSessions((prev) =>
      prev.map((s) => {
        if (s.id === currentSession.id) {
          const isFirstMessage = s.messages.length === 0;
          return {
            ...s,
            title: isFirstMessage
              ? question.length > 36
                ? `${question.substring(0, 36)}...`
                : question
              : s.title,
            subject,
            updatedAt: new Date().toISOString(),
            messages: [...s.messages, userMessage],
          };
        }
        return s;
      })
    );

    setPending(true);

    try {
      // Call actual ConfiRoute backend
      const resultCase = await api.ask(question, options, subject, simulatedLevel);

      // Add to global cases state
      setCases((prev) => [
        resultCase,
        ...prev.filter((c) => String(c.id) !== String(resultCase.id)),
      ]);

      const aiMsgId = `msg_ai_${Date.now()}`;
      const aiMessage: ChatMessage = {
        id: aiMsgId,
        role: "assistant",
        content: resultCase.final_answer || resultCase.tier1_answer || "",
        timestamp: new Date().toISOString(),
        caseData: resultCase,
      };

      setSessions((prev) =>
        prev.map((s) => {
          if (s.id === currentSession.id) {
            return {
              ...s,
              lastCase: resultCase,
              updatedAt: new Date().toISOString(),
              messages: [...s.messages, aiMessage],
            };
          }
          return s;
        })
      );
    } catch (err: any) {
      console.error("Backend ask error:", err);
      // Fallback message indicating error
      const errorMsgId = `msg_ai_err_${Date.now()}`;
      const errorMessage: ChatMessage = {
        id: errorMsgId,
        role: "assistant",
        content: `Error: ${err.message || "Unable to reach ConfiRoute backend."}`,
        timestamp: new Date().toISOString(),
      };

      setSessions((prev) =>
        prev.map((s) => {
          if (s.id === currentSession.id) {
            return {
              ...s,
              updatedAt: new Date().toISOString(),
              messages: [...s.messages, errorMessage],
            };
          }
          return s;
        })
      );
    } finally {
      setPending(false);
    }
  };

  // Regenerate last response
  const handleRegenerate = () => {
    const lastUserMsg = [...currentSession.messages].reverse().find((m) => m.role === "user");
    if (lastUserMsg) {
      handleSendMessage(
        lastUserMsg.content,
        lastUserMsg.options || null,
        lastUserMsg.subject || "General Medicine"
      );
    }
  };

  // Quick preset selection
  const handleSelectPreset = (preset: Preset) => {
    setCurrentView("chat");
    handleSendMessage(preset.question, preset.options, preset.subject, preset.sim_level);
  };

  // Callback when a review decision is recorded
  const handleReviewSuccess = (
    caseId: string | number,
    decision: string,
    finalAnswer: string | null
  ) => {
    // Update cases list
    setCases((prev) =>
      prev.map((c) => {
        if (String(c.id) === String(caseId)) {
          return {
            ...c,
            status: "resolved",
            final_answer: finalAnswer,
            review: {
              decision: decision as any,
              edited_answer: finalAnswer,
              note: "Reviewed in workspace",
              reviewer: reviewerName,
              ts: new Date().toISOString(),
            },
          };
        }
        return c;
      })
    );

    // Update in session messages
    setSessions((prev) =>
      prev.map((s) => ({
        ...s,
        messages: s.messages.map((m) => {
          if (m.caseData && String(m.caseData.id) === String(caseId)) {
            const updatedCase: Case = {
              ...m.caseData,
              status: "resolved",
              final_answer: finalAnswer,
              review: {
                decision: decision as any,
                edited_answer: finalAnswer,
                note: "Reviewed in workspace",
                reviewer: reviewerName,
                ts: new Date().toISOString(),
              },
            };
            return {
              ...m,
              caseData: updatedCase,
              content: finalAnswer || m.content,
            };
          }
          return m;
        }),
      }))
    );
  };

  // Pending reviews count
  const pendingReviewsCount = cases.filter((c) => c.status === "pending").length;

  // Show Login Page if not authenticated
  if (isLoading) {
    return (
      <div className="min-h-screen w-full flex items-center justify-center bg-[#F8F5EF]">
        <div className="w-8 h-8 border-3 border-[#C5A878] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  return (
    <div className="min-h-screen w-full flex bg-[#F8F5EF] overflow-hidden text-[#292720]">
      {/* Sidebar Navigation */}
      <AppSidebar
        currentView={currentView}
        setCurrentView={setCurrentView}
        sessions={sessions}
        currentSessionId={currentSession.id}
        onSelectSession={setCurrentSessionId}
        onNewSession={handleNewSession}
        onDeleteSession={handleDeleteSession}
        onSelectPreset={handleSelectPreset}
        pendingReviewsCount={pendingReviewsCount}
        onOpenSettings={() => setShowSettings(true)}
        onOpenProfile={() => setShowProfile(true)}
        mobileOpen={mobileSidebarOpen}
        setMobileOpen={setMobileSidebarOpen}
      />

      {/* Main Workspace Frame (offset for desktop sidebar) */}
      <div className="flex-1 flex flex-col min-w-0 md:ml-[290px] h-screen overflow-hidden">
        {currentView === "chat" && (
          <ChatWorkspace
            session={currentSession}
            pending={pending}
            onSendMessage={handleSendMessage}
            onRegenerate={handleRegenerate}
            onOpenReview={(c) => setReviewingCase(c)}
            onClearSession={handleClearSession}
            onSelectPreset={handleSelectPreset}
            onToggleMobileSidebar={() => setMobileSidebarOpen(true)}
          />
        )}

        {currentView === "queue" && (
          <ReviewQueueView
            cases={cases}
            reviewer={reviewerName}
            onOpenReview={(c) => setReviewingCase(c)}
            onRefresh={reloadCases}
            onToggleMobileSidebar={() => setMobileSidebarOpen(true)}
          />
        )}

        {currentView === "compare" && (
          <SideBySideView onToggleMobileSidebar={() => setMobileSidebarOpen(true)} />
        )}

        {currentView === "analytics" && (
          <AnalyticsView onToggleMobileSidebar={() => setMobileSidebarOpen(true)} />
        )}
      </div>

      {/* Interactive Review Modal */}
      {reviewingCase && (
        <ReviewModal
          caseData={reviewingCase}
          reviewerName={reviewerName}
          onClose={() => setReviewingCase(null)}
          onSuccess={handleReviewSuccess}
        />
      )}

      {/* Settings Modal */}
      {showSettings && (
        <SettingsModal
          reviewerName={reviewerName}
          setReviewerName={setReviewerName}
          onClose={() => setShowSettings(false)}
        />
      )}

      {/* Profile Modal */}
      {showProfile && <ProfileModal onClose={() => setShowProfile(false)} />}
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
}
