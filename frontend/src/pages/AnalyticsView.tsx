import React, { useEffect, useState } from "react";
import {
  BarChart3,
  TrendingUp,
  Download,
  Database,
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Sparkles,
  Menu,
} from "lucide-react";
import { api } from "../lib/api";
import type { SystemStats, AlertItem } from "../types";

interface AnalyticsViewProps {
  onToggleMobileSidebar: () => void;
}

export default function AnalyticsView({ onToggleMobileSidebar }: AnalyticsViewProps) {
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [seedNotice, setSeedNotice] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [statsData, alertsData] = await Promise.all([api.getStats(), api.getAlerts()]);
      setStats(statsData);
      setAlerts(alertsData);
    } catch (e) {
      console.error("Failed to load analytics:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSeed = async () => {
    setSeeding(true);
    setSeedNotice(null);
    try {
      const res = await api.seed(20);
      setSeedNotice(`Seeded ${res.count} MedMCQA clinical cases successfully.`);
      await loadData();
    } catch (err: any) {
      setSeedNotice(err.message || "Failed to seed benchmark traffic.");
    } finally {
      setSeeding(false);
    }
  };

  const total = stats?.total_queries || 0;
  const direct = stats?.routes.direct || 0;
  const tier2 = stats?.routes.tier2 || 0;
  const human = stats?.routes.human || 0;

  const directPct = total > 0 ? Math.round((direct / total) * 100) : 0;
  const tier2Pct = total > 0 ? Math.round((tier2 / total) * 100) : 0;
  const humanPct = total > 0 ? Math.round((human / total) * 100) : 0;

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
                System Diagnostics & Audit Telemetry
              </h2>
            </div>
            <p className="text-[11px] text-[#8C877B] hidden sm:block">
              Real-time routing throughput, confidence calibration, and safety alerts
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Export CSV link */}
          <a
            href={api.getExportCSVUrl()}
            download
            className="py-1.5 px-3 rounded-xl border border-[#E8E2D5] bg-[#FFFEFC] text-xs font-semibold text-[#4A473E] hover:bg-[#FAF8F5] transition-colors flex items-center gap-1.5 cursor-pointer shadow-2xs"
          >
            <Download className="w-3.5 h-3.5 text-[#C5A878]" />
            <span className="hidden sm:inline">Export Audit CSV</span>
          </a>

          {/* Seed Button */}
          <button
            onClick={handleSeed}
            disabled={seeding}
            className="py-1.5 px-3 rounded-xl bg-[#25241F] text-[#FAF8F5] text-xs font-semibold hover:bg-[#1A1916] transition-colors flex items-center gap-1.5 cursor-pointer shadow-2xs"
          >
            {seeding ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin text-[#C5A878]" />
            ) : (
              <Database className="w-3.5 h-3.5 text-[#C5A878]" />
            )}
            <span>Seed 20 Cases</span>
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto px-4 sm:px-8 py-6 max-w-6xl w-full mx-auto">
        {seedNotice && (
          <div className="mb-6 p-4 rounded-2xl bg-[#EDF5F0] border border-[#B8D9C3] text-xs text-[#29573B] flex items-center gap-2 animate-fade-in">
            <CheckCircle2 className="w-4 h-4 text-[#3E7B54]" />
            <span>{seedNotice}</span>
          </div>
        )}

        {/* Top Metric Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 mb-6">
          <div className="p-5 rounded-2xl bg-[#FFFEFC] border border-[#E8E2D5] shadow-xs">
            <span className="text-[10px] font-mono uppercase text-[#8C877B] font-semibold block">
              Total Ingested Inquiries
            </span>
            <div className="mt-2 text-2xl font-bold font-mono text-[#292720]">{total}</div>
            <span className="text-[11px] text-[#777267] mt-1 block">Production SQLite DB</span>
          </div>

          <div className="p-5 rounded-2xl bg-[#FFFEFC] border border-[#B8D9C3] shadow-xs">
            <span className="text-[10px] font-mono uppercase text-[#3E7B54] font-semibold block">
              Direct Released (High Conf)
            </span>
            <div className="mt-2 text-2xl font-bold font-mono text-[#3E7B54]">
              {direct} <span className="text-sm font-normal text-[#777267]">({directPct}%)</span>
            </div>
            <span className="text-[11px] text-[#777267] mt-1 block">Tier 1 Accepted</span>
          </div>

          <div className="p-5 rounded-2xl bg-[#FFFEFC] border border-[#F0CCA0] shadow-xs">
            <span className="text-[10px] font-mono uppercase text-[#C67D26] font-semibold block">
              Tier 2 Escalations
            </span>
            <div className="mt-2 text-2xl font-bold font-mono text-[#C67D26]">
              {tier2} <span className="text-sm font-normal text-[#777267]">({tier2Pct}%)</span>
            </div>
            <span className="text-[11px] text-[#777267] mt-1 block">Strong LLM Verified</span>
          </div>

          <div className="p-5 rounded-2xl bg-[#FFFEFC] border border-[#E8B6AF] shadow-xs">
            <span className="text-[10px] font-mono uppercase text-[#BD4C3D] font-semibold block">
              Human Review Safety Gate
            </span>
            <div className="mt-2 text-2xl font-bold font-mono text-[#BD4C3D]">
              {human} <span className="text-sm font-normal text-[#777267]">({humanPct}%)</span>
            </div>
            <span className="text-[11px] text-[#777267] mt-1 block">Clinician Held</span>
          </div>
        </div>

        {/* Triage Distribution Bar */}
        <div className="p-6 rounded-3xl bg-[#FFFEFC] border border-[#E8E2D5] shadow-xs mb-6">
          <h3 className="text-sm font-heading font-bold text-[#292720] mb-3">
            Traffic Triage Distribution
          </h3>
          <div className="h-4 w-full bg-[#E8E2D5] rounded-full overflow-hidden flex">
            <div
              style={{ width: `${directPct}%` }}
              className="bg-[#3E7B54] h-full transition-all duration-500"
              title={`Direct: ${directPct}%`}
            />
            <div
              style={{ width: `${tier2Pct}%` }}
              className="bg-[#C67D26] h-full transition-all duration-500"
              title={`Tier 2: ${tier2Pct}%`}
            />
            <div
              style={{ width: `${humanPct}%` }}
              className="bg-[#BD4C3D] h-full transition-all duration-500"
              title={`Human Review: ${humanPct}%`}
            />
          </div>

          <div className="mt-4 flex flex-wrap items-center justify-between text-xs font-mono text-[#777267]">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-[#3E7B54]" />
              <span>Direct Answer: {directPct}%</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-[#C67D26]" />
              <span>Tier 2 Strong LLM: {tier2Pct}%</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-[#BD4C3D]" />
              <span>Human Clinician Gate: {humanPct}%</span>
            </div>
          </div>
        </div>

        {/* Clinician Review Throughput & Operational Alerts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pb-12">
          {/* Review Actions */}
          <div className="p-6 rounded-3xl bg-[#FFFEFC] border border-[#E8E2D5] shadow-xs">
            <h3 className="text-sm font-heading font-bold text-[#292720] mb-4">
              Clinician Audit Resolutions
            </h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 rounded-xl bg-[#FAF8F5] border border-[#E8E2D5] text-xs">
                <span className="text-[#656056]">Pending in Queue:</span>
                <span className="font-mono font-bold text-[#BD4C3D]">
                  {stats?.reviews.pending || 0}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-xl bg-[#FAF8F5] border border-[#E8E2D5] text-xs">
                <span className="text-[#656056]">Clinician Approved:</span>
                <span className="font-mono font-bold text-[#3E7B54]">
                  {stats?.reviews.approved || 0}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-xl bg-[#FAF8F5] border border-[#E8E2D5] text-xs">
                <span className="text-[#656056]">Clinician Corrected:</span>
                <span className="font-mono font-bold text-[#C67D26]">
                  {stats?.reviews.edited || 0}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-xl bg-[#FAF8F5] border border-[#E8E2D5] text-xs">
                <span className="text-[#656056]">Clinician Rejected:</span>
                <span className="font-mono font-bold text-[#863327]">
                  {stats?.reviews.rejected || 0}
                </span>
              </div>
            </div>
          </div>

          {/* Active Safety Alerts */}
          <div className="p-6 rounded-3xl bg-[#FFFEFC] border border-[#E8E2D5] shadow-xs">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-heading font-bold text-[#292720]">
                Active Safety Alerts ({alerts.length})
              </h3>
              <button
                onClick={loadData}
                disabled={loading}
                className="text-xs text-[#8C7349] hover:underline flex items-center gap-1 cursor-pointer"
              >
                <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} />
                <span>Refresh</span>
              </button>
            </div>

            {alerts.length === 0 ? (
              <div className="p-8 text-center text-xs text-[#777267] rounded-xl bg-[#FAF8F5] border border-[#E8E2D5]">
                <CheckCircle2 className="w-8 h-8 text-[#3E7B54] mx-auto mb-2 opacity-80" />
                <span>Zero threshold or safety violations triggered. System running smoothly.</span>
              </div>
            ) : (
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {alerts.map((a, i) => (
                  <div
                    key={i}
                    className="p-3 rounded-xl bg-[#FDF1EF] border border-[#E8B6AF] text-xs text-[#6F2E24] flex items-start gap-2.5"
                  >
                    <AlertTriangle className="w-4 h-4 text-[#BD4C3D] shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <span className="font-semibold block text-[#BD4C3D]">{a.alert_type}</span>
                      <p className="mt-0.5">{a.message}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
