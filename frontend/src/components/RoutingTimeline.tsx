import React, { useState } from "react";
import {
  ChevronDown,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Cpu,
  Layers,
  ShieldCheck,
  UserCheck,
  Info,
  Sparkles,
  ArrowRight,
  ShieldAlert,
} from "lucide-react";
import type { Case } from "../types";
import ConfidenceGauge from "./ConfidenceGauge";

interface RoutingTimelineProps {
  caseData: Case;
  onOpenReview?: (caseData: Case) => void;
}

export default function RoutingTimeline({ caseData, onOpenReview }: RoutingTimelineProps) {
  const [expanded, setExpanded] = useState(false);

  // Extract actual backend values
  const score = caseData.score ?? 0;
  const percentage = Math.round(score * 100);
  const band = caseData.band || (score >= 0.8 ? "green" : score >= 0.5 ? "yellow" : "red");
  const route = caseData.route; // "direct" | "tier2" | "human"
  const isEscalated = caseData.tier_used === 2 || route === "tier2";
  const isHighRisk = caseData.risk_flag;
  const isPendingReview = caseData.status === "pending" || route === "human" && !caseData.review;
  const hasReview = !!caseData.review;

  // Initial model name
  const initialModel = "Tier 1: Llama 3.2 3B";
  const strongerModel = isEscalated ? "Tier 2: GPT-OSS 120B" : "Not applicable";

  // Classification styling
  const classification =
    band === "green"
      ? { label: "High Confidence", color: "#3E7B54", bg: "#EDF5F0", border: "#B8D9C3" }
      : band === "yellow"
      ? { label: "Medium Confidence", color: "#C67D26", bg: "#FDF5EB", border: "#F0CCA0" }
      : { label: "Low Confidence / High Risk", color: "#BD4C3D", bg: "#FDF1EF", border: "#E8B6AF" };

  // Routing Decision Display
  const routingDecisionLabel =
    route === "direct"
      ? "Direct Answer Accepted"
      : route === "tier2"
      ? "Escalated to Tier 2 Model"
      : "Clinical Review Required";

  // Human verification status
  let humanStatus = "Not required";
  if (isPendingReview) {
    humanStatus = "Pending Review";
  } else if (hasReview && caseData.review) {
    humanStatus =
      caseData.review.decision === "approve"
        ? `Approved by ${caseData.review.reviewer || "Clinician"}`
        : caseData.review.decision === "edit"
        ? `Corrected by ${caseData.review.reviewer || "Clinician"}`
        : `Rejected by ${caseData.review.reviewer || "Clinician"}`;
  }

  // Final response status
  const finalStatus =
    caseData.status === "answered"
      ? "Answer Delivered"
      : caseData.status === "resolved"
      ? "Delivered Post-Review"
      : "Draft Held for Safety";

  // Signals (s1, s2, s3)
  const s1 = caseData.signals?.s1 ?? 0;
  const s2 = caseData.signals?.s2 ?? 0;
  const s3 = caseData.signals?.s3 ?? 0;

  return (
    <div className="mt-4 overflow-hidden rounded-2xl bg-[#FFFEFC] border border-[#E8E2D5] shadow-xs">
      {/* Compact Routing Summary Header */}
      <div className="p-4 sm:p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 bg-[#FAF7F2]/60">
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Confidence Badge */}
          <span
            className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold"
            style={{
              backgroundColor: classification.bg,
              color: classification.color,
              border: `1px solid ${classification.border}`,
            }}
          >
            <span
              className="w-1.5 h-1.5 rounded-full"
              style={{ backgroundColor: classification.color }}
            />
            {percentage}% · {classification.label}
          </span>

          {/* Routing Decision Chip */}
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-[#FFFEFC] border border-[#E8E2D5] text-[#292720]">
            <Layers className="w-3.5 h-3.5 text-[#C5A878]" />
            {routingDecisionLabel}
          </span>

          {/* High-Risk Rule Warning if triggered */}
          {isHighRisk && (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-[#FDF1EF] text-[#BD4C3D] border border-[#E8B6AF]">
              <ShieldAlert className="w-3.5 h-3.5" />
              Safety Rule Active
            </span>
          )}

          {/* Status Chip */}
          <span
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono ${
              finalStatus === "Draft Held for Safety"
                ? "bg-[#FDF1EF] text-[#BD4C3D] border border-[#E8B6AF]"
                : "bg-[#EDF5F0] text-[#3E7B54] border border-[#B8D9C3]"
            }`}
          >
            {finalStatus}
          </span>
        </div>

        {/* Action button to expand/collapse details */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#8C7349] hover:text-[#5F4E30] transition-colors py-1 px-2 rounded-lg hover:bg-[#F0EBE2]/70 cursor-pointer self-start md:self-auto"
        >
          <span>{expanded ? "Hide Details" : "How ConfiRoute handled this response"}</span>
          <ChevronDown
            className={`w-4 h-4 transition-transform duration-200 ${
              expanded ? "rotate-180" : ""
            }`}
          />
        </button>
      </div>

      {/* Expanded Step-by-Step Intelligence Timeline */}
      {expanded && (
        <div className="p-5 sm:p-6 border-t border-[#E8E2D5] bg-[#FFFEFC] animate-fade-in">
          {/* Routing Fact Strip */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3.5 mb-6 rounded-xl bg-[#FAF8F4] border border-[#EBE4D7] text-xs">
            <div>
              <span className="text-[#8C877B] block font-mono text-[10px] uppercase">Initial Model</span>
              <span className="font-semibold text-[#292720] mt-0.5 block">{initialModel}</span>
            </div>
            <div>
              <span className="text-[#8C877B] block font-mono text-[10px] uppercase">Confidence Score</span>
              <span className="font-semibold text-[#292720] mt-0.5 block font-mono">
                {score.toFixed(2)} ({percentage}%)
              </span>
            </div>
            <div>
              <span className="text-[#8C877B] block font-mono text-[10px] uppercase">Escalation Status</span>
              <span className="font-semibold text-[#292720] mt-0.5 block">
                {isEscalated ? "Escalated (Tier 2)" : "None"}
              </span>
            </div>
            <div>
              <span className="text-[#8C877B] block font-mono text-[10px] uppercase">Verification Status</span>
              <span className="font-semibold text-[#292720] mt-0.5 block truncate">
                {humanStatus}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* 6-Stage Timeline Flow */}
            <div className="lg:col-span-8 space-y-4">
              <h4 className="text-xs font-mono uppercase tracking-wider text-[#777267] font-semibold mb-3">
                Execution Stages & Safety Gates
              </h4>

              {/* Stage 1: Query Ingestion */}
              <div className="flex items-start gap-3 relative pb-4 border-l-2 border-[#E8E2D5] ml-3 pl-4">
                <span className="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-[#3E7B54] text-white flex items-center justify-center text-[9px] font-bold">
                  1
                </span>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-[#292720]">Query Received & Risk Scan</span>
                    <span className="text-[10px] font-mono text-[#8C877B]">Domain: {caseData.subject || "General"}</span>
                  </div>
                  <p className="text-xs text-[#777267] mt-0.5 leading-relaxed">
                    Query analyzed for clinical contraindications and critical dosage terms.
                    {isHighRisk && (
                      <span className="text-[#BD4C3D] font-medium block mt-0.5">
                        Rule triggered: "{caseData.risk_reason || "Critical medication dosage detected"}".
                      </span>
                    )}
                  </p>
                </div>
              </div>

              {/* Stage 2: Initial Model Generation */}
              <div className="flex items-start gap-3 relative pb-4 border-l-2 border-[#E8E2D5] ml-3 pl-4">
                <span className="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-[#B79A68] text-white flex items-center justify-center text-[9px] font-bold">
                  2
                </span>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-[#292720]">Initial Model Generation</span>
                    <span className="text-[10px] font-mono text-[#8C877B]">llama 3.2 3B</span>
                  </div>
                  <p className="text-xs text-[#777267] mt-0.5 leading-relaxed">
                    Lightweight tier generated draft answer with logprob telemetry.
                  </p>
                </div>
              </div>

              {/* Stage 3: Confidence Multi-Signal Computation */}
              <div className="flex items-start gap-3 relative pb-4 border-l-2 border-[#E8E2D5] ml-3 pl-4">
                <span className="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-[#B79A68] text-white flex items-center justify-center text-[9px] font-bold">
                  3
                </span>
                <div className="w-full">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-[#292720]">Confidence Evaluation Performed</span>
                    <span className="text-xs font-mono font-bold text-[#C67D26]">Score: {score.toFixed(2)}</span>
                  </div>

                  {/* 3-Signal Breakdown Cards */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mt-2">
                    <div className="p-2 rounded-lg bg-[#FAF8F5] border border-[#E8E2D5]">
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="text-[#777267]">Token Probs (s₁)</span>
                        <span className="font-mono font-semibold text-[#292720]">{s1.toFixed(2)}</span>
                      </div>
                      <div className="mt-1 h-1.5 w-full bg-[#E8E2D5] rounded-full overflow-hidden">
                        <div
                          className="h-full bg-[#3E7B54] rounded-full"
                          style={{ width: `${Math.min(100, Math.round(s1 * 100))}%` }}
                        />
                      </div>
                      <span className="text-[9px] text-[#A8A296] font-mono mt-0.5 block">Weight: 40%</span>
                    </div>

                    <div className="p-2 rounded-lg bg-[#FAF8F5] border border-[#E8E2D5]">
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="text-[#777267]">Consistency (s₂)</span>
                        <span className="font-mono font-semibold text-[#292720]">{s2.toFixed(2)}</span>
                      </div>
                      <div className="mt-1 h-1.5 w-full bg-[#E8E2D5] rounded-full overflow-hidden">
                        <div
                          className="h-full bg-[#C67D26] rounded-full"
                          style={{ width: `${Math.min(100, Math.round(s2 * 100))}%` }}
                        />
                      </div>
                      <span className="text-[9px] text-[#A8A296] font-mono mt-0.5 block">Weight: 30%</span>
                    </div>

                    <div className="p-2 rounded-lg bg-[#FAF8F5] border border-[#E8E2D5]">
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="text-[#777267]">Self-Rating (s₃)</span>
                        <span className="font-mono font-semibold text-[#292720]">{s3.toFixed(2)}</span>
                      </div>
                      <div className="mt-1 h-1.5 w-full bg-[#E8E2D5] rounded-full overflow-hidden">
                        <div
                          className="h-full bg-[#B79A68] rounded-full"
                          style={{ width: `${Math.min(100, Math.round(s3 * 100))}%` }}
                        />
                      </div>
                      <span className="text-[9px] text-[#A8A296] font-mono mt-0.5 block">Weight: 30%</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Stage 4: Routing Decision Made */}
              <div className="flex items-start gap-3 relative pb-4 border-l-2 border-[#E8E2D5] ml-3 pl-4">
                <span className="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-[#25241F] text-white flex items-center justify-center text-[9px] font-bold">
                  4
                </span>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-[#292720]">Routing Decision Made</span>
                    <span className="text-[10px] font-mono text-[#8C877B]">
                      Threshold check: ≥0.80 direct, 0.50–0.79 escalate
                    </span>
                  </div>
                  <p className="text-xs text-[#777267] mt-0.5 leading-relaxed">
                    {caseData.reason || "Evaluated by ConfiRoute rule engine."}
                  </p>
                </div>
              </div>

              {/* Stage 5: Escalation or Human Review */}
              <div className="flex items-start gap-3 relative pb-4 border-l-2 border-[#E8E2D5] ml-3 pl-4">
                <span className="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-[#C5A878] text-white flex items-center justify-center text-[9px] font-bold">
                  5
                </span>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-[#292720]">
                      {isEscalated
                        ? "Tier 2 Escalation Executed"
                        : route === "human"
                        ? "Safety Gate: Clinician Review"
                        : "Escalation Not Required"}
                    </span>
                  </div>
                  <p className="text-xs text-[#777267] mt-0.5 leading-relaxed">
                    {isEscalated
                      ? `Re-evaluated with higher-capacity model (${strongerModel}).`
                      : route === "human"
                      ? "Uncertainty below threshold or critical safety rule active. Answer routed to clinical review queue."
                      : "Direct pathway satisfied with high statistical certainty."}
                  </p>

                  {/* Clinician Review Details if resolved */}
                  {hasReview && caseData.review && (
                    <div className="mt-2 p-2.5 rounded-lg bg-[#FAF7F2] border border-[#E8E2D5] text-xs">
                      <div className="font-semibold text-[#292720]">
                        Reviewed by {caseData.review.reviewer}:{" "}
                        <span className="capitalize">{caseData.review.decision}</span>
                      </div>
                      {caseData.review.note && (
                        <p className="text-[#656056] text-[11px] mt-0.5 italic">
                          "{caseData.review.note}"
                        </p>
                      )}
                    </div>
                  )}

                  {/* If still pending review, offer quick review modal */}
                  {isPendingReview && onOpenReview && (
                    <button
                      onClick={() => onOpenReview(caseData)}
                      className="mt-2 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#25241F] text-white text-xs font-semibold hover:bg-[#38362E] transition-all cursor-pointer shadow-xs"
                    >
                      <UserCheck className="w-3.5 h-3.5 text-[#C5A878]" />
                      <span>Review as Clinician</span>
                    </button>
                  )}
                </div>
              </div>

              {/* Stage 6: Final Response Delivered */}
              <div className="flex items-start gap-3 relative ml-3 pl-4">
                <span className="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-[#3E7B54] text-white flex items-center justify-center text-[9px] font-bold">
                  6
                </span>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-[#292720]">Final Response Status</span>
                    <span className="text-[10px] font-mono text-[#3E7B54] font-medium">{finalStatus}</span>
                  </div>
                  <p className="text-xs text-[#777267] mt-0.5 leading-relaxed">
                    {finalStatus === "Draft Held for Safety"
                      ? "Answer draft is withheld from the end-user pending human clinical audit."
                      : "Verified answer delivered to chat workspace with transparent routing provenance."}
                  </p>
                </div>
              </div>
            </div>

            {/* Gauge & Metrics Breakdown Card */}
            <div className="lg:col-span-4 flex flex-col justify-between p-4 rounded-xl bg-[#FAF8F4] border border-[#EBE4D7]">
              <div>
                <h5 className="text-xs font-mono uppercase text-[#777267] font-semibold text-center mb-1">
                  Evaluated Confidence
                </h5>
                <ConfidenceGauge score={score} band={band} size={150} showLabel={true} />

                {/* Disclaimer note */}
                <div className="mt-4 p-2.5 rounded-lg bg-[#FFFEFC] border border-[#E8E2D5] text-[11px] text-[#777267] leading-relaxed">
                  <div className="flex items-center gap-1 font-semibold text-[#292720] mb-0.5">
                    <Info className="w-3 h-3 text-[#B79A68]" />
                    <span>Confidence Notice</span>
                  </div>
                  Confidence evaluates token probability and consistency. It does not imply infallible mathematical truth.
                </div>
              </div>

              {/* Cost & Calls Telemetry */}
              <div className="mt-4 pt-3 border-t border-[#E8E2D5] text-xs font-mono text-[#777267] space-y-1">
                <div className="flex justify-between">
                  <span>LLM Invocations:</span>
                  <span className="text-[#292720] font-semibold">{caseData.calls || 1}</span>
                </div>
                <div className="flex justify-between">
                  <span>Equiv Token Cost:</span>
                  <span className="text-[#292720] font-semibold">
                    ${(caseData.cost_equiv ?? 0).toFixed(6)}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
