import React, { useState } from "react";
import { X, UserCheck, CheckCircle2, Edit3, XCircle, AlertTriangle, ShieldCheck } from "lucide-react";
import type { Case } from "../types";
import { api } from "../lib/api";

interface ReviewModalProps {
  caseData: Case | null;
  reviewerName: string;
  onClose: () => void;
  onSuccess: (updatedCaseId: string | number, decision: string, finalAnswer: string | null) => void;
}

export default function ReviewModal({
  caseData,
  reviewerName,
  onClose,
  onSuccess,
}: ReviewModalProps) {
  if (!caseData) return null;

  const [decision, setDecision] = useState<"approve" | "edit" | "reject">("approve");
  const [editedAnswer, setEditedAnswer] = useState(caseData.tier1_answer || "");
  const [currentReviewer, setCurrentReviewer] = useState(reviewerName || "Dr. Sarah Chen");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (decision === "edit" && !editedAnswer.trim()) {
      setError("Please provide the corrected answer before submitting an 'edit' review.");
      return;
    }

    setSubmitting(true);
    try {
      const resp = await api.review(
        caseData.id,
        decision,
        decision === "edit" ? editedAnswer.trim() : null,
        notes.trim(),
        currentReviewer || "Dr. Sarah Chen"
      );
      onSuccess(caseData.id, resp.decision, resp.final_answer);
      onClose();
    } catch (err: any) {
      console.error("Failed to submit review:", err);
      setError(err.message || "Failed to submit review to backend.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#25241F]/60 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-xl rounded-3xl bg-[#FFFEFC] border border-[#E8E2D5] p-6 sm:p-8 shadow-2xl relative max-h-[90vh] overflow-y-auto">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-2 rounded-xl text-[#8C877B] hover:text-[#292720] hover:bg-[#F0EBE2] transition-colors cursor-pointer"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="flex items-center gap-3 mb-6 pb-4 border-b border-[#F1ECE2]">
          <div className="w-10 h-10 rounded-xl bg-[#25241F] flex items-center justify-center shadow-xs">
            <UserCheck className="w-5 h-5 text-[#C5A878]" />
          </div>
          <div>
            <h3 className="text-xl font-heading font-bold text-[#292720]">
              Clinical Case Review & Verification
            </h3>
            <p className="text-xs text-[#777267] font-mono">
              Case ID: {caseData.id} · Specialty: {caseData.subject || "General"}
            </p>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-xl bg-[#FDF1EF] border border-[#E8B6AF] text-xs text-[#BD4C3D] flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Case Details */}
        <div className="space-y-4 mb-6">
          <div className="p-4 rounded-xl bg-[#FAF8F5] border border-[#E8E2D5]">
            <span className="text-[10px] font-mono uppercase text-[#8C877B] font-semibold block mb-1">
              Patient / Clinical Question
            </span>
            <p className="text-sm font-medium text-[#292720]">{caseData.question}</p>

            {caseData.options && (
              <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-xs">
                {Object.entries(caseData.options).map(([k, v]) => (
                  <div key={k} className="p-1.5 rounded bg-white border border-[#E8E2D5]">
                    <strong className="text-[#8C7349] mr-1">{k}:</strong>
                    <span className="text-[#4A473E]">{v}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="p-4 rounded-xl bg-[#FAF8F5] border border-[#E8E2D5]">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] font-mono uppercase text-[#8C877B] font-semibold">
                AI Draft Answer (Tier 1)
              </span>
              <span className="text-xs font-mono font-bold text-[#BD4C3D]">
                Score: {caseData.score.toFixed(2)}
              </span>
            </div>
            <p className="text-sm text-[#292720]">{caseData.tier1_answer || "No draft answer"}</p>
            {caseData.risk_flag && (
              <span className="inline-block mt-2 text-[11px] text-[#BD4C3D] font-medium">
                ⚠ Risk Reason: {caseData.risk_reason || "Critical medication / clinical keyword rule"}
              </span>
            )}
          </div>
        </div>

        {/* Review Form */}
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Action Choice Pills */}
          <div>
            <label className="block text-xs font-semibold text-[#4A473E] tracking-wider uppercase mb-2">
              Clinician Action
            </label>
            <div className="grid grid-cols-3 gap-2.5">
              <button
                type="button"
                onClick={() => setDecision("approve")}
                className={`py-3 px-3 rounded-xl border text-xs font-semibold flex flex-col items-center justify-center gap-1.5 transition-all cursor-pointer ${
                  decision === "approve"
                    ? "bg-[#EDF5F0] border-[#3E7B54] text-[#29573B] shadow-xs"
                    : "bg-[#FFFEFC] border-[#E8E2D5] text-[#777267] hover:bg-[#F0EBE2]"
                }`}
              >
                <CheckCircle2 className="w-4 h-4 text-[#3E7B54]" />
                <span>Approve Draft</span>
              </button>

              <button
                type="button"
                onClick={() => setDecision("edit")}
                className={`py-3 px-3 rounded-xl border text-xs font-semibold flex flex-col items-center justify-center gap-1.5 transition-all cursor-pointer ${
                  decision === "edit"
                    ? "bg-[#FDF5EB] border-[#C67D26] text-[#8A5010] shadow-xs"
                    : "bg-[#FFFEFC] border-[#E8E2D5] text-[#777267] hover:bg-[#F0EBE2]"
                }`}
              >
                <Edit3 className="w-4 h-4 text-[#C67D26]" />
                <span>Edit Answer</span>
              </button>

              <button
                type="button"
                onClick={() => setDecision("reject")}
                className={`py-3 px-3 rounded-xl border text-xs font-semibold flex flex-col items-center justify-center gap-1.5 transition-all cursor-pointer ${
                  decision === "reject"
                    ? "bg-[#FDF1EF] border-[#BD4C3D] text-[#863327] shadow-xs"
                    : "bg-[#FFFEFC] border-[#E8E2D5] text-[#777267] hover:bg-[#F0EBE2]"
                }`}
              >
                <XCircle className="w-4 h-4 text-[#BD4C3D]" />
                <span>Reject & Withhold</span>
              </button>
            </div>
          </div>

          {/* Corrected Answer Input (if editing) */}
          {decision === "edit" && (
            <div className="animate-fade-in">
              <label className="block text-xs font-semibold text-[#4A473E] tracking-wider uppercase mb-1.5">
                Corrected Clinical Answer
              </label>
              <textarea
                value={editedAnswer}
                onChange={(e) => setEditedAnswer(e.target.value)}
                rows={3}
                required
                className="w-full p-3 bg-[#FAF8F5] border border-[#E8E2D5] rounded-xl text-xs sm:text-sm text-[#292720] focus:outline-none focus:ring-2 focus:ring-[#C5A878]"
                placeholder="Enter the clinically verified answer or option..."
              />
            </div>
          )}

          {/* Reviewer Assignment */}
          <div>
            <label className="block text-xs font-semibold text-[#4A473E] tracking-wider uppercase mb-1.5">
              Assigned Clinician Auditor
            </label>
            <input
              type="text"
              value={currentReviewer}
              onChange={(e) => setCurrentReviewer(e.target.value)}
              placeholder="e.g. Dr. Sarah Chen"
              required
              className="w-full px-3.5 py-2.5 bg-[#FAF8F5] border border-[#E8E2D5] rounded-xl text-xs text-[#292720] focus:outline-none focus:ring-2 focus:ring-[#C5A878]"
            />
          </div>

          {/* Audit Notes */}
          <div>
            <label className="block text-xs font-semibold text-[#4A473E] tracking-wider uppercase mb-1.5">
              Clinical Audit Justification Note (Optional)
            </label>
            <input
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Verified contraindication in third trimester..."
              className="w-full px-3.5 py-2.5 bg-[#FAF8F5] border border-[#E8E2D5] rounded-xl text-xs text-[#292720] focus:outline-none focus:ring-2 focus:ring-[#C5A878]"
            />
          </div>

          {/* Reviewer signature notice */}
          <div className="text-[11px] text-[#8C877B] flex items-center justify-between pt-1">
            <span>Signing Reviewer: <strong>{currentReviewer || "Dr. Sarah Chen"}</strong></span>
            <span className="font-mono text-[#3E7B54]">Authenticated Audit</span>
          </div>

          {/* Submit Actions */}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-3 rounded-xl border border-[#E8E2D5] text-xs font-semibold text-[#6B665A] hover:bg-[#F0EBE2] transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="flex-1 py-3 rounded-xl bg-[#25241F] text-[#FAF8F5] text-xs font-semibold hover:bg-[#1A1916] transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-60 shadow-md"
            >
              {submitting ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Recording Audit...</span>
                </>
              ) : (
                <>
                  <ShieldCheck className="w-4 h-4 text-[#C5A878]" />
                  <span>Confirm Clinical Action</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
