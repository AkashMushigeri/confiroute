import React, { useEffect, useState } from "react";
import { X, Settings, Server, Cpu, Sliders, CheckCircle2, AlertCircle, RefreshCw } from "lucide-react";
import { api } from "../lib/api";

interface SettingsModalProps {
  reviewerName: string;
  setReviewerName: (name: string) => void;
  onClose: () => void;
}

export default function SettingsModal({
  reviewerName,
  setReviewerName,
  onClose,
}: SettingsModalProps) {
  const [healthStatus, setHealthStatus] = useState<{
    status: string;
    app_name: string;
    is_mock_mode: boolean;
  } | null>(null);
  const [loadingHealth, setLoadingHealth] = useState(false);
  const [localName, setLocalName] = useState(reviewerName);
  const [savedToast, setSavedToast] = useState(false);

  const checkHealth = async () => {
    setLoadingHealth(true);
    try {
      const data = await api.health();
      setHealthStatus(data);
    } catch {
      setHealthStatus(null);
    } finally {
      setLoadingHealth(false);
    }
  };

  useEffect(() => {
    checkHealth();
  }, []);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setReviewerName(localName.trim() || "Dr. Sarah Chen");
    setSavedToast(true);
    setTimeout(() => setSavedToast(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#25241F]/60 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-lg rounded-3xl bg-[#FFFEFC] border border-[#E8E2D5] p-6 sm:p-8 shadow-2xl relative max-h-[90vh] overflow-y-auto">
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-2 rounded-xl text-[#8C877B] hover:text-[#292720] hover:bg-[#F0EBE2] transition-colors cursor-pointer"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-6 pb-4 border-b border-[#F1ECE2]">
          <div className="w-10 h-10 rounded-xl bg-[#25241F] flex items-center justify-center shadow-xs">
            <Settings className="w-5 h-5 text-[#C5A878]" />
          </div>
          <div>
            <h3 className="text-xl font-heading font-bold text-[#292720]">System & Reviewer Settings</h3>
            <p className="text-xs text-[#777267]">ConfiRoute Calibration and Telemetry</p>
          </div>
        </div>

        {/* Backend Connectivity Status */}
        <div className="p-4 rounded-2xl bg-[#FAF8F5] border border-[#E8E2D5] mb-5">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-[#292720]">
              <Server className="w-4 h-4 text-[#C5A878]" />
              <span>FastAPI REST Backend</span>
            </div>
            <button
              onClick={checkHealth}
              disabled={loadingHealth}
              className="text-[11px] text-[#8C7349] hover:underline flex items-center gap-1 cursor-pointer"
            >
              <RefreshCw className={`w-3 h-3 ${loadingHealth ? "animate-spin" : ""}`} />
              Test Ping
            </button>
          </div>

          {healthStatus ? (
            <div className="flex items-center gap-2 text-xs text-[#3E7B54]">
              <CheckCircle2 className="w-4 h-4" />
              <span>
                Connected to <strong>{healthStatus.app_name}</strong> (Port 8000) · Mock Mode:{" "}
                <strong>{healthStatus.is_mock_mode ? "Active" : "Disabled (Live LLM)"}</strong>
              </span>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-xs text-[#BD4C3D]">
              <AlertCircle className="w-4 h-4" />
              <span>
                Backend offline or unreachable. Please launch via <code>run_app.ps1</code>.
              </span>
            </div>
          )}
        </div>

        {/* Reviewer Identity */}
        <form onSubmit={handleSave} className="space-y-4 mb-6">
          <div>
            <label className="block text-xs font-semibold text-[#4A473E] tracking-wider uppercase mb-1.5">
              Clinician Auditor Name
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={localName}
                onChange={(e) => setLocalName(e.target.value)}
                placeholder="Dr. Sarah Chen"
                className="flex-1 px-3.5 py-2.5 bg-[#FAF8F5] border border-[#E8E2D5] rounded-xl text-xs text-[#292720] focus:outline-none focus:ring-2 focus:ring-[#C5A878]"
              />
              <button
                type="submit"
                className="px-4 py-2.5 rounded-xl bg-[#25241F] text-xs font-semibold text-[#F8F5EF] hover:bg-[#1A1916] transition-colors cursor-pointer"
              >
                Update
              </button>
            </div>
            {savedToast && (
              <span className="text-[11px] text-[#3E7B54] font-medium mt-1 inline-block">
                ✓ Auditor name updated
              </span>
            )}
          </div>
        </form>

        {/* Model Architecture Info */}
        <div className="mb-6 space-y-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-[#4A473E] tracking-wider uppercase">
            <Cpu className="w-4 h-4 text-[#C5A878]" />
            <span>LLM Tiers Configured</span>
          </div>
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="p-3 rounded-xl bg-[#FAF8F5] border border-[#E8E2D5]">
              <div className="font-semibold text-[#292720]">Tier 1: Initial Model</div>
              <div className="font-mono text-[#8C877B] text-[11px] mt-0.5">llama3.2:3b</div>
              <div className="text-[10px] text-[#3E7B54] mt-1 font-mono">Logprobs Enabled</div>
            </div>
            <div className="p-3 rounded-xl bg-[#FAF8F5] border border-[#E8E2D5]">
              <div className="font-semibold text-[#292720]">Tier 2: Escalation Model</div>
              <div className="font-mono text-[#8C877B] text-[11px] mt-0.5">gpt-oss-120b</div>
              <div className="text-[10px] text-[#C67D26] mt-1 font-mono">High-Capacity Verification</div>
            </div>
          </div>
        </div>

        {/* Routing Thresholds */}
        <div className="mb-6 space-y-2">
          <div className="flex items-center gap-2 text-xs font-semibold text-[#4A473E] tracking-wider uppercase">
            <Sliders className="w-4 h-4 text-[#C5A878]" />
            <span>Calibrated Routing Boundaries</span>
          </div>
          <div className="p-3 rounded-xl bg-[#FAF8F5] border border-[#E8E2D5] text-xs space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-[#656056]">Direct Release (Green):</span>
              <span className="font-mono font-bold text-[#3E7B54]">Score ≥ 0.80</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-[#656056]">Tier 2 Escalation (Yellow):</span>
              <span className="font-mono font-bold text-[#C67D26]">0.50 ≤ Score &lt; 0.80</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-[#656056]">Clinical Review Gate (Red):</span>
              <span className="font-mono font-bold text-[#BD4C3D]">Score &lt; 0.50 or High Risk</span>
            </div>
          </div>
        </div>

        <button
          onClick={onClose}
          className="w-full py-3 rounded-xl bg-[#F0EBE2] text-xs font-semibold text-[#292720] hover:bg-[#E5DEC9] transition-colors cursor-pointer"
        >
          Close Settings
        </button>
      </div>
    </div>
  );
}
