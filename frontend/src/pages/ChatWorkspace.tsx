import React, { useState, useRef, useEffect } from "react";
import {
  Send,
  Loader2,
  Sparkles,
  ShieldCheck,
  ChevronDown,
  Layers,
  Cpu,
  UserCheck,
  RotateCcw,
  PlusCircle,
  Download,
  Trash2,
  Menu,
} from "lucide-react";
import type { ChatSession, Case } from "../types";
import ChatMessageItem from "../components/ChatMessageItem";
import { PRESETS, type Preset } from "../lib/api";

interface ChatWorkspaceProps {
  session: ChatSession;
  pending: boolean;
  onSendMessage: (
    question: string,
    options: { A: string; B: string; C: string; D: string } | null,
    subject: string,
    simulatedLevel?: string
  ) => void;
  onRegenerate: () => void;
  onOpenReview: (caseData: Case) => void;
  onClearSession: () => void;
  onSelectPreset: (preset: Preset) => void;
  onToggleMobileSidebar: () => void;
}

export default function ChatWorkspace({
  session,
  pending,
  onSendMessage,
  onRegenerate,
  onOpenReview,
  onClearSession,
  onSelectPreset,
  onToggleMobileSidebar,
}: ChatWorkspaceProps) {
  const [inputText, setInputText] = useState("");
  const [showOptions, setShowOptions] = useState(false);
  const [options, setOptions] = useState({ A: "", B: "", C: "", D: "" });
  const [subject, setSubject] = useState(session.subject || "General Medicine");
  const [simLevel, setSimLevel] = useState<string>("");

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [session.messages, pending]);

  // Auto-resize textarea
  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputText(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    const query = inputText.trim();
    if (!query || pending) return;

    const hasOptions =
      options.A.trim() || options.B.trim() || options.C.trim() || options.D.trim();

    onSendMessage(
      query,
      hasOptions
        ? {
            A: options.A.trim(),
            B: options.B.trim(),
            C: options.C.trim(),
            D: options.D.trim(),
          }
        : null,
      subject,
      simLevel || undefined
    );

    setInputText("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const hasMessages = session.messages.length > 0;

  return (
    <div className="flex-1 flex flex-col h-screen overflow-hidden bg-[#F8F5EF] relative">
      {/* Workspace Header */}
      <header className="h-16 px-4 sm:px-8 border-b border-[#E8E2D5] bg-[#FFFEFC]/80 backdrop-blur-md flex items-center justify-between shrink-0 z-20">
        <div className="flex items-center gap-3">
          <button
            onClick={onToggleMobileSidebar}
            className="p-2 rounded-xl text-[#777267] hover:text-[#292720] hover:bg-[#F0EBE2] md:hidden cursor-pointer"
          >
            <Menu className="w-5 h-5" />
          </button>

          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm sm:text-base font-heading font-bold text-[#292720] truncate max-w-[200px] sm:max-w-md">
                {session.title || "Clinical Inquiry Workspace"}
              </h2>
              <span className="hidden sm:inline-flex px-2 py-0.5 rounded-full text-[10px] font-mono bg-[#FAF8F5] text-[#777267] border border-[#E8E2D5]">
                {subject}
              </span>
            </div>
            <p className="text-[11px] text-[#8C877B] hidden sm:block">
              Confidence-Aware LLM Routing · 3-Tier Multi-Signal Triage
            </p>
          </div>
        </div>

        {/* Header Action Tools */}
        <div className="flex items-center gap-2">
          {hasMessages && (
            <button
              onClick={onClearSession}
              title="Clear session history"
              className="p-2 rounded-xl text-[#8C877B] hover:text-[#BD4C3D] hover:bg-[#FDF1EF] transition-colors cursor-pointer text-xs flex items-center gap-1.5"
            >
              <Trash2 className="w-4 h-4" />
              <span className="hidden sm:inline">Clear Chat</span>
            </button>
          )}

          {/* Model Status Strip */}
          <div className="hidden lg:flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#FAF8F5] border border-[#E8E2D5] text-[11px] font-mono">
            <span className="w-2 h-2 rounded-full bg-[#3E7B54]" />
            <span className="text-[#656056]">T1: Llama3.2</span>
            <span className="text-[#A8A296]">→</span>
            <span className="text-[#656056]">T2: GPT-OSS</span>
            <span className="text-[#A8A296]">→</span>
            <span className="text-[#8C7349]">Clinician</span>
          </div>
        </div>
      </header>

      {/* Main Conversation Stream */}
      <main className="flex-1 overflow-y-auto px-4 sm:px-8 py-6 max-w-4xl w-full mx-auto">
        {!hasMessages ? (
          /* Welcome Screen */
          <div className="h-full flex flex-col justify-center items-center text-center max-w-2xl mx-auto py-12 animate-fade-in">
            <div className="w-16 h-16 rounded-3xl bg-gradient-to-br from-[#25241F] to-[#38362E] flex items-center justify-center shadow-lg border border-[#C5A878]/30 mb-6">
              <ShieldCheck className="w-8 h-8 text-[#C5A878]" />
            </div>

            <h1 className="text-2xl sm:text-3xl font-heading font-extrabold text-[#292720] tracking-tight">
              Confidence-Aware Medical Intelligence
            </h1>
            <p className="mt-3 text-sm text-[#777267] leading-relaxed max-w-lg">
              ConfiRoute eliminates blind LLM hallucinations by calculating token probabilities, self-consistency, and safety overrides before answering, escalating to stronger models, or routing to human clinicians.
            </p>

            {/* Visual 3-Tier Workflow Card */}
            <div className="w-full mt-8 grid grid-cols-1 sm:grid-cols-3 gap-3 text-left">
              <div className="p-4 rounded-2xl bg-[#FFFEFC] border border-[#E8E2D5] shadow-2xs">
                <div className="w-7 h-7 rounded-lg bg-[#EDF5F0] border border-[#B8D9C3] flex items-center justify-center mb-2.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#3E7B54]" />
                </div>
                <div className="text-xs font-bold text-[#292720]">Direct Answer</div>
                <div className="text-[10px] font-mono text-[#3E7B54] mb-1">Score ≥ 0.80</div>
                <p className="text-[11px] text-[#777267] leading-snug">
                  High statistical certainty; answer delivered immediately with full transparency.
                </p>
              </div>

              <div className="p-4 rounded-2xl bg-[#FFFEFC] border border-[#E8E2D5] shadow-2xs">
                <div className="w-7 h-7 rounded-lg bg-[#FDF5EB] border border-[#F0CCA0] flex items-center justify-center mb-2.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#C67D26]" />
                </div>
                <div className="text-xs font-bold text-[#292720]">Tier 2 Escalation</div>
                <div className="text-[10px] font-mono text-[#C67D26] mb-1">0.50 ≤ Score &lt; 0.80</div>
                <p className="text-[11px] text-[#777267] leading-snug">
                  Moderate ambiguity triggers a higher-capacity LLM for second-stage verification.
                </p>
              </div>

              <div className="p-4 rounded-2xl bg-[#FFFEFC] border border-[#E8E2D5] shadow-2xs">
                <div className="w-7 h-7 rounded-lg bg-[#FDF1EF] border border-[#E8B6AF] flex items-center justify-center mb-2.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#BD4C3D]" />
                </div>
                <div className="text-xs font-bold text-[#292720]">Clinician Review</div>
                <div className="text-[10px] font-mono text-[#BD4C3D] mb-1">Score &lt; 0.50 / Risk</div>
                <p className="text-[11px] text-[#777267] leading-snug">
                  Uncertain or critical-dosage inquiries are held in the clinical review queue.
                </p>
              </div>
            </div>

            {/* Suggested Benchmark Presets */}
            <div className="w-full mt-8">
              <span className="text-[11px] font-mono uppercase tracking-wider text-[#8C877B] block mb-2.5">
                Quick Test Benchmark Questions
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-left">
                {PRESETS.slice(0, 4).map((p) => (
                  <button
                    key={p.key}
                    onClick={() => onSelectPreset(p)}
                    className="p-3 rounded-xl bg-[#FFFEFC] hover:bg-[#FAF8F5] border border-[#E8E2D5] hover:border-[#C5A878] text-xs transition-all cursor-pointer group shadow-2xs"
                  >
                    <div className="flex items-center justify-between font-semibold text-[#292720] group-hover:text-[#8C7349]">
                      <span>{p.label}</span>
                      <span className="font-mono text-[10px] text-[#8C877B]">
                        {p.subject}
                      </span>
                    </div>
                    <p className="text-[11px] text-[#777267] line-clamp-1 mt-1">{p.question}</p>
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          /* Chat Message Stream */
          <div className="space-y-2 pb-6">
            {session.messages.map((msg) => (
              <ChatMessageItem
                key={msg.id}
                message={msg}
                onRegenerate={onRegenerate}
                onOpenReview={onOpenReview}
              />
            ))}

            {/* Pending Inference & Confidence Scoring Indicator */}
            {pending && (
              <div className="flex justify-start mb-6 animate-fade-in">
                <div className="w-full max-w-[85%] flex items-start gap-3.5">
                  <div className="w-9 h-9 rounded-xl bg-[#25241F] flex items-center justify-center shrink-0 shadow-sm mt-1">
                    <Loader2 className="w-5 h-5 text-[#C5A878] animate-spin" />
                  </div>
                  <div className="flex-1 rounded-2xl bg-[#FFFEFC] border border-[#E8E2D5] p-5 shadow-sm">
                    <div className="flex items-center gap-2 text-xs font-semibold text-[#292720] mb-2">
                      <Sparkles className="w-4 h-4 text-[#C5A878] animate-pulse" />
                      <span>ConfiRoute Triage Engine Computing...</span>
                    </div>
                    <div className="space-y-2">
                      <div className="h-4 bg-[#F0EBE2] rounded-md animate-shimmer w-3/4" />
                      <div className="h-4 bg-[#F0EBE2] rounded-md animate-shimmer w-1/2" />
                    </div>
                    <div className="mt-4 pt-3 border-t border-[#F1ECE2] flex items-center justify-between text-[11px] text-[#8C877B] font-mono">
                      <span>Signal Extraction (s1: logprobs, s2: consistency, s3: rating)</span>
                      <span className="text-[#C67D26]">Calculating Certainty</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </main>

      {/* Floating Bottom Input Area */}
      <footer className="p-4 sm:p-6 bg-gradient-to-t from-[#F8F5EF] via-[#F8F5EF]/95 to-transparent shrink-0">
        <div className="max-w-4xl mx-auto w-full">
          {/* Options & Specialty Pill Selectors */}
          <div className="flex flex-wrap items-center justify-between gap-2 mb-2 px-1 text-xs">
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setShowOptions(!showOptions)}
                className={`px-2.5 py-1 rounded-lg border text-[11px] font-medium flex items-center gap-1.5 transition-colors cursor-pointer ${
                  showOptions
                    ? "bg-[#FAF8F5] border-[#C5A878] text-[#8C7349]"
                    : "bg-[#FFFEFC] border-[#E8E2D5] text-[#656056] hover:bg-[#FAF8F5]"
                }`}
              >
                <span>MCQ Options (A-D)</span>
                <ChevronDown
                  className={`w-3 h-3 transition-transform ${showOptions ? "rotate-180" : ""}`}
                />
              </button>

              {/* Specialty Selector */}
              <select
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className="px-2.5 py-1 rounded-lg bg-[#FFFEFC] border border-[#E8E2D5] text-[11px] text-[#4A473E] focus:outline-none focus:ring-1 focus:ring-[#C5A878] cursor-pointer"
              >
                <option value="General Medicine">General Medicine</option>
                <option value="Pharmacology">Pharmacology</option>
                <option value="Cardiology">Cardiology</option>
                <option value="Physiology">Physiology</option>
                <option value="Pathology">Pathology</option>
                <option value="Surgery">Surgery</option>
              </select>

              {/* Simulation Preset Selector */}
              <select
                value={simLevel}
                onChange={(e) => setSimLevel(e.target.value)}
                className="px-2.5 py-1 rounded-lg bg-[#FFFEFC] border border-[#E8E2D5] text-[11px] text-[#4A473E] focus:outline-none focus:ring-1 focus:ring-[#C5A878] cursor-pointer"
              >
                <option value="">Simulation: Auto</option>
                <option value="high">Force High Certainty (Green)</option>
                <option value="medium">Force Ambiguity (Yellow)</option>
                <option value="low">Force Low / Review (Red)</option>
              </select>
            </div>

            <span className="hidden sm:inline text-[11px] text-[#A8A296] font-mono">
              Press Enter to submit · Shift+Enter for newline
            </span>
          </div>

          {/* Expandable Multiple Choice Options Box */}
          {showOptions && (
            <div className="mb-2.5 p-3 rounded-2xl bg-[#FFFEFC] border border-[#E8E2D5] grid grid-cols-1 sm:grid-cols-2 gap-2 animate-fade-in shadow-xs">
              <input
                type="text"
                placeholder="Option A"
                value={options.A}
                onChange={(e) => setOptions({ ...options, A: e.target.value })}
                className="px-3 py-1.5 rounded-lg bg-[#FAF8F5] border border-[#E8E2D5] text-xs text-[#292720] focus:outline-none focus:ring-1 focus:ring-[#C5A878]"
              />
              <input
                type="text"
                placeholder="Option B"
                value={options.B}
                onChange={(e) => setOptions({ ...options, B: e.target.value })}
                className="px-3 py-1.5 rounded-lg bg-[#FAF8F5] border border-[#E8E2D5] text-xs text-[#292720] focus:outline-none focus:ring-1 focus:ring-[#C5A878]"
              />
              <input
                type="text"
                placeholder="Option C"
                value={options.C}
                onChange={(e) => setOptions({ ...options, C: e.target.value })}
                className="px-3 py-1.5 rounded-lg bg-[#FAF8F5] border border-[#E8E2D5] text-xs text-[#292720] focus:outline-none focus:ring-1 focus:ring-[#C5A878]"
              />
              <input
                type="text"
                placeholder="Option D"
                value={options.D}
                onChange={(e) => setOptions({ ...options, D: e.target.value })}
                className="px-3 py-1.5 rounded-lg bg-[#FAF8F5] border border-[#E8E2D5] text-xs text-[#292720] focus:outline-none focus:ring-1 focus:ring-[#C5A878]"
              />
            </div>
          )}

          {/* Main Input Box */}
          <form
            onSubmit={handleSubmit}
            className="relative flex items-end rounded-2xl bg-[#FFFEFC] border border-[#E8E2D5] shadow-md focus-within:border-[#C5A878] focus-within:ring-2 focus-within:ring-[#C5A878]/30 transition-all p-2"
          >
            <textarea
              ref={textareaRef}
              rows={1}
              value={inputText}
              onChange={handleTextareaChange}
              onKeyDown={handleKeyDown}
              placeholder="Ask ConfiRoute anything... (e.g., dosage protocols, differential diagnosis, pathology)"
              disabled={pending}
              className="w-full resize-none bg-transparent px-3 py-2 text-sm text-[#292720] placeholder-[#A8A296] focus:outline-none max-h-44 disabled:opacity-60"
            />

            <button
              type="submit"
              disabled={pending || !inputText.trim()}
              className="p-2.5 rounded-xl bg-[#25241F] text-[#FAF8F5] hover:bg-[#1A1916] disabled:opacity-40 disabled:cursor-not-allowed transition-all cursor-pointer shrink-0 shadow-xs ml-2"
            >
              {pending ? (
                <Loader2 className="w-4 h-4 animate-spin text-[#C5A878]" />
              ) : (
                <Send className="w-4 h-4 text-[#C5A878]" />
              )}
            </button>
          </form>
        </div>
      </footer>
    </div>
  );
}
