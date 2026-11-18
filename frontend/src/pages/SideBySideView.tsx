import { useState, useEffect } from "react";
import {
  AlertTriangle,
  ShieldCheck,
  ShieldAlert,
  Loader2,
  Menu,
} from "lucide-react";
import { api, PRESETS, type Preset } from "../lib/api";
import type { CompareResponse } from "../types";
import RoutingTimeline from "../components/RoutingTimeline";

interface SideBySideViewProps {
  onToggleMobileSidebar: () => void;
}

export default function SideBySideView({ onToggleMobileSidebar }: SideBySideViewProps) {
  const [selectedPreset, setSelectedPreset] = useState<Preset>(PRESETS[2]); // High risk default
  const [customQuestion, setCustomQuestion] = useState(PRESETS[2].question);
  const [customOptions, setCustomOptions] = useState(PRESETS[2].options || { A: "", B: "", C: "", D: "" });
  const [loading, setLoading] = useState(false);
  const [compareData, setCompareData] = useState<CompareResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const runComparison = async (q: string, opts: any, subj: string, simLevel?: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.compare(q, opts, subj, simLevel);
      setCompareData(result);
    } catch (err: any) {
      console.error("Comparison run failed:", err);
      setError(err.message || "Failed to run comparison with backend.");
    } finally {
      setLoading(false);
    }
  };

  const handleSelectPreset = (p: Preset) => {
    setSelectedPreset(p);
    setCustomQuestion(p.question);
    if (p.options) setCustomOptions(p.options);
    runComparison(p.question, p.options, p.subject, p.sim_level);
  };

  // Run initial comparison on mount
  useEffect(() => {
    runComparison(selectedPreset.question, selectedPreset.options, selectedPreset.subject, selectedPreset.sim_level);
  }, []);

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
                Side-by-Side Safety Comparison
              </h2>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-[#FDF5EB] text-[#C67D26] border border-[#F0CCA0]">
                Baseline B0 vs ConfiRoute B3
              </span>
            </div>
            <p className="text-[11px] text-[#8C877B] hidden sm:block">
              Demonstrates why raw unrouted LLMs are hazardous in clinical & critical decision-making
            </p>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto px-4 sm:px-8 py-6 max-w-6xl w-full mx-auto">
        {/* Preset Selector Banner */}
        <div className="mb-6 p-4 rounded-2xl bg-[#FFFEFC] border border-[#E8E2D5] shadow-xs">
          <div className="text-xs font-semibold text-[#4A473E] tracking-wider uppercase mb-2">
            Select Test Scenario
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
            {PRESETS.map((p) => {
              const isSelected = p.key === selectedPreset.key;
              return (
                <button
                  key={p.key}
                  onClick={() => handleSelectPreset(p)}
                  className={`p-2.5 rounded-xl border text-left text-xs transition-all cursor-pointer ${
                    isSelected
                      ? "bg-[#25241F] text-[#FAF8F5] border-[#25241F] shadow-xs"
                      : "bg-[#FAF8F5] text-[#292720] border-[#E8E2D5] hover:bg-[#F0EBE2]"
                  }`}
                >
                  <div className="font-semibold truncate">{p.label}</div>
                  <div
                    className={`text-[10px] font-mono mt-0.5 ${
                      isSelected ? "text-[#C5A878]" : "text-[#777267]"
                    }`}
                  >
                    {p.subject}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-2xl bg-[#FDF1EF] border border-[#E8B6AF] text-xs text-[#BD4C3D] flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Current Question In Review */}
        <div className="mb-6 p-5 rounded-2xl bg-[#FFFEFC] border border-[#E8E2D5] shadow-xs">
          <span className="text-[10px] font-mono uppercase text-[#8C877B] font-semibold block mb-1">
            Evaluated Medical Query
          </span>
          <h3 className="text-base font-semibold text-[#292720]">{customQuestion}</h3>

          {customOptions && (
            <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
              {Object.entries(customOptions).map(([k, v]) => (
                <div key={k} className="p-2 rounded-lg bg-[#FAF8F5] border border-[#E8E2D5]">
                  <strong className="text-[#8C7349] mr-1.5">{k}:</strong>
                  <span className="text-[#4A473E]">{v}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Comparison Columns */}
        {loading ? (
          <div className="py-20 text-center">
            <Loader2 className="w-8 h-8 text-[#C5A878] animate-spin mx-auto mb-3" />
            <span className="text-xs font-mono text-[#777267]">
              Querying baseline and executing ConfiRoute confidence routing...
            </span>
          </div>
        ) : compareData ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pb-12 animate-fade-in">
            {/* Left Column: Blind Unrouted LLM (B0) */}
            <div className="rounded-3xl bg-[#FFFEFC] border-2 border-[#E8B6AF] p-6 shadow-sm flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between pb-3 mb-4 border-b border-[#F1ECE2]">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-xl bg-[#FDF1EF] border border-[#E8B6AF] flex items-center justify-center">
                      <ShieldAlert className="w-4 h-4 text-[#BD4C3D]" />
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-[#292720]">Standard Unrouted LLM</h4>
                      <span className="text-[10px] font-mono text-[#BD4C3D]">Baseline B0 · Zero Triage</span>
                    </div>
                  </div>
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-[#FDF1EF] text-[#BD4C3D] border border-[#E8B6AF]">
                    UNGUARDED RELEASE
                  </span>
                </div>

                <div className="p-3.5 rounded-xl bg-[#FDF1EF] border border-[#E8B6AF] text-xs text-[#6F2E24] mb-4">
                  <div className="font-semibold flex items-center gap-1.5 mb-1 text-[#BD4C3D]">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    <span>Inherent Clinical Risk:</span>
                  </div>
                  {compareData.unrouted.warning}
                </div>

                <div className="space-y-2 mb-6">
                  <span className="text-[10px] font-mono uppercase text-[#8C877B] font-semibold block">
                    Direct Output Generated:
                  </span>
                  <div className="p-4 rounded-xl bg-[#FAF8F5] border border-[#E8E2D5] text-sm text-[#292720] font-medium leading-relaxed">
                    {compareData.unrouted.answer}
                  </div>
                </div>
              </div>

              <div className="pt-4 border-t border-[#F1ECE2] text-[11px] text-[#8C877B] space-y-1 font-mono">
                <div className="flex justify-between">
                  <span>Uncertainty Awareness:</span>
                  <span className="text-[#BD4C3D] font-bold">None (0%)</span>
                </div>
                <div className="flex justify-between">
                  <span>Safety Overrides:</span>
                  <span className="text-[#BD4C3D] font-bold">Disabled</span>
                </div>
              </div>
            </div>

            {/* Right Column: ConfiRoute System (B3) */}
            <div className="rounded-3xl bg-[#FFFEFC] border-2 border-[#B8D9C3] p-6 shadow-sm flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between pb-3 mb-4 border-b border-[#F1ECE2]">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-xl bg-[#EDF5F0] border border-[#B8D9C3] flex items-center justify-center">
                      <ShieldCheck className="w-4 h-4 text-[#3E7B54]" />
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-[#292720]">ConfiRoute Guarded System</h4>
                      <span className="text-[10px] font-mono text-[#3E7B54]">Production B3 · Safety Layer</span>
                    </div>
                  </div>
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-[#EDF5F0] text-[#3E7B54] border border-[#B8D9C3]">
                    CONFIDENCE ROUTED
                  </span>
                </div>

                <div className="space-y-2 mb-6">
                  <span className="text-[10px] font-mono uppercase text-[#8C877B] font-semibold block">
                    ConfiRoute Triage Outcome:
                  </span>
                  <div className="p-4 rounded-xl bg-[#FAF8F5] border border-[#E8E2D5] text-sm text-[#292720] leading-relaxed">
                    {compareData.confiroute.status === "pending" ? (
                      <div className="text-[#BD4C3D] font-medium">
                        🛡 Output withheld for clinical review. Reason: {compareData.confiroute.reason}
                      </div>
                    ) : (
                      compareData.confiroute.final_answer || compareData.confiroute.tier1_answer
                    )}
                  </div>
                </div>

                {/* Routing Timeline Embedded */}
                <RoutingTimeline caseData={compareData.confiroute} />
              </div>

              <div className="pt-4 mt-6 border-t border-[#F1ECE2] text-[11px] text-[#8C877B] space-y-1 font-mono">
                <div className="flex justify-between">
                  <span>Routing Decision:</span>
                  <span className="text-[#3E7B54] font-bold uppercase">{compareData.confiroute.route}</span>
                </div>
                <div className="flex justify-between">
                  <span>Safety Status:</span>
                  <span className="text-[#3E7B54] font-bold">Active & Audited</span>
                </div>
              </div>
            </div>
          </div>
        ) : null}
      </main>
    </div>
  );
}
