import React, { useState } from "react";
import {
  UserCheck,
  Search,
  Filter,
  RefreshCw,
  AlertTriangle,
  Clock,
  CheckCircle2,
  Edit3,
  XCircle,
  ShieldAlert,
  ArrowRight,
  Menu,
} from "lucide-react";
import type { Case } from "../types";

interface ReviewQueueViewProps {
  cases: Case[];
  reviewer: string;
  onOpenReview: (caseData: Case) => void;
  onRefresh: () => Promise<void>;
  onToggleMobileSidebar: () => void;
}

export default function ReviewQueueView({
  cases,
  reviewer,
  onOpenReview,
  onRefresh,
  onToggleMobileSidebar,
}: ReviewQueueViewProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [subjectFilter, setSubjectFilter] = useState("All");
  const [statusFilter, setStatusFilter] = useState<"pending" | "resolved" | "all">("pending");
  const [refreshing, setRefreshing] = useState(false);

  const handleRefresh = async () => {
    setRefreshing(true);
    await onRefresh();
    setRefreshing(false);
  };

  // Filter cases
  const filteredCases = cases.filter((c) => {
    const matchesSearch =
      c.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (c.risk_reason && c.risk_reason.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesSubject = subjectFilter === "All" || c.subject === subjectFilter;

    const matchesStatus =
      statusFilter === "all"
        ? true
        : statusFilter === "pending"
        ? c.status === "pending"
        : c.status === "resolved";

    return matchesSearch && matchesSubject && matchesStatus;
  });

  const pendingCount = cases.filter((c) => c.status === "pending").length;
  const resolvedCount = cases.filter((c) => c.status === "resolved").length;

  return (
    <div className="flex-1 flex flex-col h-screen overflow-hidden bg-[#F8F5EF]">
      {/* Header */}
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
              <h2 className="text-base sm:text-lg font-heading font-bold text-[#292720]">
                Human Clinician Review Queue
              </h2>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-[#FDF1EF] text-[#BD4C3D] border border-[#E8B6AF]">
                {pendingCount} Pending
              </span>
            </div>
            <p className="text-[11px] text-[#8C877B] hidden sm:block">
              Safety-Gate Triage · Review held queries before release to users
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="py-1.5 px-3 rounded-xl border border-[#E8E2D5] bg-[#FFFEFC] text-xs font-semibold text-[#4A473E] hover:bg-[#FAF8F5] transition-colors flex items-center gap-1.5 cursor-pointer shadow-2xs"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
            <span>Refresh Queue</span>
          </button>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 overflow-y-auto px-4 sm:px-8 py-6 max-w-5xl w-full mx-auto">
        {/* Filter & Search Bar */}
        <div className="mb-6 grid grid-cols-1 sm:grid-cols-12 gap-3 p-3 rounded-2xl bg-[#FFFEFC] border border-[#E8E2D5] shadow-xs">
          <div className="sm:col-span-6 relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-3 text-[#A8A296] pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by question keywords or risk reason..."
              className="w-full pl-8 pr-3 py-2 bg-[#FAF8F5] border border-[#E8E2D5] rounded-xl text-xs text-[#292720] focus:outline-none focus:ring-1 focus:ring-[#C5A878]"
            />
          </div>

          <div className="sm:col-span-3">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as any)}
              className="w-full py-2 px-3 bg-[#FAF8F5] border border-[#E8E2D5] rounded-xl text-xs text-[#4A473E] focus:outline-none focus:ring-1 focus:ring-[#C5A878] cursor-pointer"
            >
              <option value="pending">Pending Review ({pendingCount})</option>
              <option value="resolved">Resolved Cases ({resolvedCount})</option>
              <option value="all">All Cases ({cases.length})</option>
            </select>
          </div>

          <div className="sm:col-span-3">
            <select
              value={subjectFilter}
              onChange={(e) => setSubjectFilter(e.target.value)}
              className="w-full py-2 px-3 bg-[#FAF8F5] border border-[#E8E2D5] rounded-xl text-xs text-[#4A473E] focus:outline-none focus:ring-1 focus:ring-[#C5A878] cursor-pointer"
            >
              <option value="All">All Specialties</option>
              <option value="General Medicine">General Medicine</option>
              <option value="Pharmacology">Pharmacology</option>
              <option value="Cardiology">Cardiology</option>
              <option value="Physiology">Physiology</option>
              <option value="Surgery">Surgery</option>
            </select>
          </div>
        </div>

        {/* Case Cards List */}
        {filteredCases.length === 0 ? (
          <div className="py-16 text-center rounded-3xl bg-[#FFFEFC] border border-[#E8E2D5] p-8">
            <CheckCircle2 className="w-12 h-12 text-[#3E7B54] mx-auto mb-3 opacity-80" />
            <h3 className="text-base font-heading font-bold text-[#292720]">Queue is Clear</h3>
            <p className="mt-1 text-xs text-[#777267] max-w-sm mx-auto">
              No cases matching your current filter criteria require clinical review at this time.
            </p>
          </div>
        ) : (
          <div className="space-y-4 pb-12">
            {filteredCases.map((c) => {
              const isPending = c.status === "pending";
              const isResolved = c.status === "resolved";

              return (
                <div
                  key={c.id}
                  className="rounded-2xl bg-[#FFFEFC] border border-[#E8E2D5] p-5 sm:p-6 shadow-xs hover:border-[#C5A878] transition-all"
                >
                  {/* Top Case Tag Line */}
                  <div className="flex flex-wrap items-center justify-between gap-2 pb-3 mb-3 border-b border-[#F1ECE2] text-xs">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-[#292720]">Case #{c.id}</span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-[#FAF8F5] text-[#777267] border border-[#E8E2D5]">
                        {c.subject || "General"}
                      </span>
                      {c.risk_flag && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium bg-[#FDF1EF] text-[#BD4C3D] border border-[#E8B6AF]">
                          <ShieldAlert className="w-3 h-3" />
                          Risk Override
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-3 text-xs">
                      <span className="font-mono text-[#8C877B]">
                        Certainty: <strong className="text-[#BD4C3D]">{c.score.toFixed(2)}</strong>
                      </span>
                      <span
                        className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono font-semibold ${
                          isPending
                            ? "bg-[#FDF1EF] text-[#BD4C3D] border border-[#E8B6AF]"
                            : "bg-[#EDF5F0] text-[#3E7B54] border border-[#B8D9C3]"
                        }`}
                      >
                        {isPending ? "Pending Clinician Review" : "Resolved"}
                      </span>
                    </div>
                  </div>

                  {/* Question */}
                  <h4 className="text-sm font-semibold text-[#292720] leading-snug mb-2">
                    {c.question}
                  </h4>

                  {/* Options if provided */}
                  {c.options && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 mb-3 text-xs">
                      {Object.entries(c.options).map(([k, v]) => (
                        <div key={k} className="p-1.5 rounded bg-[#FAF8F5] border border-[#E8E2D5]">
                          <strong className="text-[#8C7349] mr-1">{k}:</strong>
                          <span className="text-[#4A473E]">{v}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Draft vs Released Answer */}
                  <div className="p-3.5 rounded-xl bg-[#FAF8F5] border border-[#E8E2D5] text-xs mb-4">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[10px] font-mono uppercase text-[#8C877B] font-semibold">
                        {isPending ? "Withheld Draft Answer" : "Final Answer Delivered"}
                      </span>
                      <span className="text-[10px] font-mono text-[#8C877B]">
                        Model: {c.tier_used === 2 ? "Tier 2 (GPT-OSS)" : "Tier 1 (Llama3.2)"}
                      </span>
                    </div>
                    <p className="text-[#292720] leading-relaxed">
                      {isPending
                        ? c.tier1_answer || "No draft recorded."
                        : c.final_answer || c.tier1_answer}
                    </p>
                    {c.risk_reason && (
                      <div className="mt-2 text-[11px] text-[#BD4C3D] font-medium">
                        ⚠ Safety Trigger: {c.risk_reason}
                      </div>
                    )}
                  </div>

                  {/* Review Audit Details if already resolved */}
                  {isResolved && c.review && (
                    <div className="p-3 rounded-xl bg-[#EDF5F0] border border-[#B8D9C3] text-xs text-[#29573B] mb-4">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold">
                          Action: {c.review.decision.toUpperCase()} by {c.review.reviewer}
                        </span>
                        <span className="font-mono text-[10px]">
                          {c.review.ts ? new Date(c.review.ts).toLocaleDateString() : ""}
                        </span>
                      </div>
                      {c.review.note && (
                        <p className="mt-1 text-[11px] italic">Note: "{c.review.note}"</p>
                      )}
                    </div>
                  )}

                  {/* Action Bar */}
                  <div className="flex items-center justify-between pt-1">
                    <span className="text-[11px] font-mono text-[#8C877B]">
                      Ingested: {new Date(c.ts).toLocaleString()}
                    </span>

                    {isPending ? (
                      <button
                        onClick={() => onOpenReview(c)}
                        className="py-2 px-4 rounded-xl bg-[#25241F] text-[#FAF8F5] text-xs font-semibold hover:bg-[#1A1916] transition-all flex items-center gap-1.5 cursor-pointer shadow-xs"
                      >
                        <UserCheck className="w-3.5 h-3.5 text-[#C5A878]" />
                        <span>Review & Decide</span>
                        <ArrowRight className="w-3.5 h-3.5 ml-0.5" />
                      </button>
                    ) : (
                      <button
                        onClick={() => onOpenReview(c)}
                        className="py-1.5 px-3 rounded-xl border border-[#E8E2D5] bg-[#FFFEFC] text-xs font-medium text-[#777267] hover:bg-[#FAF8F5] transition-colors cursor-pointer"
                      >
                        Re-evaluate Case
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
