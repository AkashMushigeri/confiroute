import { useState } from "react";
import {
  ShieldCheck,
  User,
  Copy,
  Check,
  RotateCcw,
  AlertOctagon,
  UserCheck,
  AlertTriangle,
} from "lucide-react";
import type { ChatMessage, Case } from "../types";
import RoutingTimeline from "./RoutingTimeline";

interface ChatMessageItemProps {
  message: ChatMessage;
  onRegenerate?: () => void;
  onOpenReview?: (caseData: Case) => void;
}

function CodeBlock({ code, lang }: { code: string; lang?: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopyCode = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative my-3 rounded-xl bg-[#201F1B] border border-[#3E3C34] overflow-hidden text-xs font-mono shadow-sm">
      <div className="flex items-center justify-between px-3 py-1.5 bg-[#171613] border-b border-[#33312B] text-[#A8A296] text-[11px]">
        <span>{lang || "code"}</span>
        <button
          onClick={handleCopyCode}
          className="flex items-center gap-1 hover:text-[#FAF8F5] transition-colors cursor-pointer"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-[#3E7B54]" />
              <span className="text-[#3E7B54]">Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>
      <pre className="p-3.5 overflow-x-auto text-[#FAF8F5] leading-relaxed">
        <code>{code}</code>
      </pre>
    </div>
  );
}

function renderInlineMarkdown(text: string): React.ReactNode {
  // Regex to split bold (**), italic (*), and code (`)
  const parts = text.split(/(\*\*.*?\*\*|\*.*?\*|`.*?`)/g);
  return parts.map((part, idx) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={idx} className="font-semibold text-[#1F1E19]">
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith("*") && part.endsWith("*")) {
      return (
        <em key={idx} className="italic text-[#33312A]">
          {part.slice(1, -1)}
        </em>
      );
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code
          key={idx}
          className="px-1.5 py-0.5 rounded bg-[#FAF5EB] border border-[#E8DFC9] font-mono text-xs text-[#8C7349]"
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    return part;
  });
}

function renderMarkdown(content: string) {
  if (!content) return null;

  // Split into block sections (paragraphs or code blocks)
  const codeBlockRegex = /```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g;
  const elements: React.ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = codeBlockRegex.exec(content)) !== null) {
    if (match.index > lastIndex) {
      const textBefore = content.substring(lastIndex, match.index);
      elements.push(...renderTextParagraphs(textBefore, `pre_${lastIndex}`));
    }
    const lang = match[1];
    const code = match[2];
    elements.push(<CodeBlock key={`cb_${match.index}`} code={code} lang={lang} />);
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < content.length) {
    const textAfter = content.substring(lastIndex);
    elements.push(...renderTextParagraphs(textAfter, `post_${lastIndex}`));
  }

  return elements;
}

function renderTextParagraphs(text: string, keyPrefix: string): React.ReactNode[] {
  const paragraphs = text.split(/\n\n+/);
  return paragraphs.map((para, pIdx) => {
    const trimmed = para.trim();
    if (!trimmed) return null;

    // Check for Heading 3
    if (trimmed.startsWith("### ")) {
      return (
        <h4 key={`${keyPrefix}_h3_${pIdx}`} className="text-sm font-heading font-bold text-[#292720] mt-3 mb-1">
          {renderInlineMarkdown(trimmed.replace(/^###\s+/, ""))}
        </h4>
      );
    }

    // Check for Heading 2
    if (trimmed.startsWith("## ")) {
      return (
        <h3 key={`${keyPrefix}_h2_${pIdx}`} className="text-base font-heading font-bold text-[#292720] mt-3 mb-1.5">
          {renderInlineMarkdown(trimmed.replace(/^##\s+/, ""))}
        </h3>
      );
    }

    // Check for Blockquote
    if (trimmed.startsWith("> ")) {
      return (
        <blockquote
          key={`${keyPrefix}_bq_${pIdx}`}
          className="border-l-3 border-[#C5A878] pl-3.5 py-1 my-2 text-xs italic text-[#6B665A] bg-[#FAF8F4]/80 rounded-r-lg"
        >
          {renderInlineMarkdown(trimmed.replace(/^>\s+/, ""))}
        </blockquote>
      );
    }

    // Check for bullet list
    if (trimmed.includes("\n- ") || trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      const items = trimmed.split(/\n[-*]\s+/).map((s) => s.replace(/^[-*]\s+/, ""));
      return (
        <ul key={`${keyPrefix}_ul_${pIdx}`} className="list-disc pl-5 my-2 space-y-1 text-xs sm:text-sm">
          {items.map((item, iIdx) => (
            <li key={iIdx} className="leading-relaxed">
              {renderInlineMarkdown(item)}
            </li>
          ))}
        </ul>
      );
    }

    // Check for numbered list
    if (/^\d+\.\s+/.test(trimmed)) {
      const items = trimmed.split(/\n\d+\.\s+/).map((s) => s.replace(/^\d+\.\s+/, ""));
      return (
        <ol key={`${keyPrefix}_ol_${pIdx}`} className="list-decimal pl-5 my-2 space-y-1 text-xs sm:text-sm">
          {items.map((item, iIdx) => (
            <li key={iIdx} className="leading-relaxed">
              {renderInlineMarkdown(item)}
            </li>
          ))}
        </ol>
      );
    }

    return (
      <p key={`${keyPrefix}_p_${pIdx}`} className="leading-relaxed mb-2 last:mb-0 text-xs sm:text-sm text-[#292720]">
        {renderInlineMarkdown(trimmed)}
      </p>
    );
  });
}

export default function ChatMessageItem({
  message,
  onRegenerate,
  onOpenReview,
}: ChatMessageItemProps) {
  const [copied, setCopied] = useState(false);

  const isUser = message.role === "user";
  const caseData = message.caseData;

  const handleCopy = () => {
    const textToCopy =
      caseData?.final_answer || caseData?.tier1_answer || message.content;
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Determine Answer content to display for Assistant messages
  let displayAnswer = message.content;
  let isHeld = false;
  let isRejected = false;

  if (caseData) {
    if (caseData.status === "pending") {
      isHeld = true;
    } else if (caseData.status === "resolved" && caseData.review?.decision === "reject") {
      isRejected = true;
    } else if (caseData.final_answer) {
      displayAnswer = caseData.final_answer;
    } else if (caseData.tier1_answer) {
      displayAnswer = caseData.tier1_answer;
    }
  }

  if (isUser) {
    return (
      <div className="flex justify-end mb-6 animate-fade-in">
        <div className="max-w-[85%] sm:max-w-[75%] flex items-start gap-3 flex-row-reverse">
          {/* User Avatar */}
          <div className="w-8 h-8 rounded-full bg-[#E5DEC9] border border-[#D5CEBF] flex items-center justify-center shrink-0 shadow-xs">
            <User className="w-4 h-4 text-[#4A473E]" />
          </div>

          {/* User Bubble */}
          <div className="rounded-2xl rounded-tr-xs bg-[#FAF7F0] border border-[#E8E2D5] p-4 text-[#292720] shadow-xs">
            <div className="text-xs font-mono text-[#8C877B] mb-1 flex items-center justify-end gap-2">
              <span>{message.subject || "Clinical Inquiry"}</span>
              <span>·</span>
              <span>
                {new Date(message.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </span>
            </div>

            <div className="text-sm sm:text-base font-normal leading-relaxed break-words">
              {message.content}
            </div>

            {/* Candidate options if provided */}
            {message.options && (
              <div className="mt-3 pt-2.5 border-t border-[#E8E2D5]/70 grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-xs">
                {Object.entries(message.options).map(([optKey, optVal]) => (
                  <div key={optKey} className="flex items-start gap-1.5 p-1.5 rounded-lg bg-[#FFFEFC] border border-[#E8E2D5]">
                    <span className="font-mono font-bold text-[#8C7349] shrink-0">{optKey}.</span>
                    <span className="text-[#4A473E]">{optVal}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Assistant AI Message
  return (
    <div className="flex justify-start mb-8 animate-fade-in">
      <div className="w-full max-w-[94%] sm:max-w-[88%] flex items-start gap-3.5">
        {/* ConfiRoute AI Avatar */}
        <div className="w-9 h-9 rounded-xl bg-[#25241F] border border-[#C5A878]/40 flex items-center justify-center shrink-0 shadow-sm mt-1">
          <ShieldCheck className="w-5 h-5 text-[#C5A878]" />
        </div>

        {/* AI Card Content */}
        <div className="flex-1 min-w-0">
          <div className="rounded-2xl bg-[#FFFEFC] border border-[#E8E2D5] p-5 sm:p-6 shadow-sm">
            {/* Header info */}
            <div className="flex items-center justify-between pb-3 mb-3 border-b border-[#F1ECE2] text-xs">
              <div className="flex items-center gap-2">
                <span className="font-heading font-bold text-[#25241F]">ConfiRoute AI</span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-[#F0EBE2] text-[#777267] border border-[#E8E2D5]">
                  {caseData ? "EVALUATED" : "SYSTEM"}
                </span>
              </div>

              <div className="flex items-center gap-2 text-[#8C877B]">
                <span className="text-[11px] font-mono">
                  {new Date(message.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </span>

                {/* Copy button */}
                <button
                  onClick={handleCopy}
                  title="Copy answer"
                  className="p-1 rounded-md hover:bg-[#F0EBE2] text-[#777267] hover:text-[#292720] transition-colors cursor-pointer"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-[#3E7B54]" /> : <Copy className="w-3.5 h-3.5" />}
                </button>

                {/* Regenerate button */}
                {onRegenerate && (
                  <button
                    onClick={onRegenerate}
                    title="Regenerate evaluation"
                    className="p-1 rounded-md hover:bg-[#F0EBE2] text-[#777267] hover:text-[#292720] transition-colors cursor-pointer"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>

            {/* Error banner if message failed */}
            {message.error && (
              <div className="mb-3 p-3 rounded-xl bg-[#FDF1EF] border border-[#E8B6AF] text-xs text-[#BD4C3D] flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{message.error}</span>
              </div>
            )}

            {/* Answer Display */}
            {isHeld ? (
              <div className="p-4 rounded-xl bg-[#FDF1EF] border border-[#E8B6AF] my-2">
                <div className="flex items-center gap-2.5 text-[#BD4C3D] font-semibold text-sm mb-1">
                  <AlertOctagon className="w-4 h-4 shrink-0" />
                  <span>Clinical Safety Hold Active</span>
                </div>
                <p className="text-xs text-[#6F2E24] leading-relaxed">
                  This query triggered a safety hold because the computed confidence score was below the safety threshold (0.50) or flagged a critical clinical keyword. The draft answer is currently withheld from the patient/user.
                </p>
                {onOpenReview && caseData && (
                  <button
                    onClick={() => onOpenReview(caseData)}
                    className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#25241F] text-[#FAF8F5] text-xs font-semibold hover:bg-[#3D3A31] transition-all cursor-pointer shadow-xs"
                  >
                    <UserCheck className="w-3.5 h-3.5 text-[#C5A878]" />
                    <span>Review & Authorize in Clinical Queue</span>
                  </button>
                )}
              </div>
            ) : isRejected ? (
              <div className="p-4 rounded-xl bg-[#FDF1EF] border border-[#E8B6AF] my-2">
                <div className="flex items-center gap-2 text-[#BD4C3D] font-semibold text-sm mb-1">
                  <AlertOctagon className="w-4 h-4" />
                  <span>Response Rejected by Reviewer</span>
                </div>
                <p className="text-xs text-[#6F2E24]">
                  A human clinician reviewed and rejected the draft answer. No answer was released.
                  {caseData?.review?.note && ` Note: "${caseData.review.note}"`}
                </p>
              </div>
            ) : (
              <div className="prose-confiroute text-sm sm:text-base text-[#292720]">
                {renderMarkdown(displayAnswer)}
              </div>
            )}

            {/* Clinician Review Resolution Banner if already resolved */}
            {caseData?.review && caseData.status === "resolved" && (
              <div className="mt-3 p-3 rounded-xl bg-[#EDF5F0] border border-[#B8D9C3] flex items-center justify-between text-xs text-[#29573B]">
                <div className="flex items-center gap-2">
                  <UserCheck className="w-4 h-4 text-[#3E7B54]" />
                  <span>
                    Clinician Audit: <strong className="capitalize">{caseData.review.decision}</strong> by{" "}
                    <strong>{caseData.review.reviewer}</strong>
                  </span>
                </div>
                <span className="font-mono text-[10px] text-[#3E7B54]">VERIFIED</span>
              </div>
            )}

            {/* Routing Timeline & Intelligence Visualization */}
            {caseData && <RoutingTimeline caseData={caseData} onOpenReview={onOpenReview} />}
          </div>
        </div>
      </div>
    </div>
  );
}

