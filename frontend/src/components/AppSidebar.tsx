import React, { useState } from "react";
import {
  ShieldCheck,
  Plus,
  Search,
  MessageSquare,
  UserCheck,
  GitCompare,
  BarChart3,
  Settings,
  LogOut,
  ChevronRight,
  Trash2,
  Sparkles,
  X,
  Radio,
  Stethoscope,
} from "lucide-react";
import type { ChatSession, ViewMode } from "../types";
import { PRESETS, type Preset } from "../lib/api";
import { useAuth } from "../context/AuthContext";

interface AppSidebarProps {
  currentView: ViewMode;
  setCurrentView: (view: ViewMode) => void;
  sessions: ChatSession[];
  currentSessionId: string;
  onSelectSession: (id: string) => void;
  onNewSession: () => void;
  onDeleteSession: (id: string) => void;
  onSelectPreset: (preset: Preset) => void;
  pendingReviewsCount: number;
  onOpenSettings: () => void;
  onOpenProfile: () => void;
  mobileOpen: boolean;
  setMobileOpen: (open: boolean) => void;
}

export default function AppSidebar({
  currentView,
  setCurrentView,
  sessions,
  currentSessionId,
  onSelectSession,
  onNewSession,
  onDeleteSession,
  onSelectPreset,
  pendingReviewsCount,
  onOpenSettings,
  onOpenProfile,
  mobileOpen,
  setMobileOpen,
}: AppSidebarProps) {
  const { user, logout } = useAuth();
  const [searchQuery, setSearchQuery] = useState("");
  const [showPresets, setShowPresets] = useState(false);

  // Filter sessions by search query
  const filteredSessions = sessions.filter((s) =>
    s.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <>
      {/* Mobile Backdrop */}
      {mobileOpen && (
        <div
          onClick={() => setMobileOpen(false)}
          className="fixed inset-0 z-40 bg-[#25241F]/50 backdrop-blur-xs md:hidden"
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 w-[290px] bg-[#FAF8F5] border-r border-[#E8E2D5] flex flex-col justify-between transition-transform duration-300 ease-in-out md:translate-x-0 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Top Header & Brand */}
        <div className="p-4 border-b border-[#E8E2D5]">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-[#25241F] flex items-center justify-center shadow-xs">
                <ShieldCheck className="w-4 h-4 text-[#C5A878]" />
              </div>
              <div>
                <span className="font-heading font-extrabold text-base text-[#25241F] tracking-tight">
                  ConfiRoute
                </span>
                <span className="block text-[10px] font-mono text-[#8C877B] tracking-wider uppercase">
                  Confidence Layer
                </span>
              </div>
            </div>

            <button
              onClick={() => setMobileOpen(false)}
              className="p-1 rounded-lg text-[#8C877B] hover:text-[#292720] md:hidden cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* New Session Button */}
          <button
            onClick={() => {
              onNewSession();
              setCurrentView("chat");
              setMobileOpen(false);
            }}
            className="w-full py-2.5 px-3.5 rounded-xl bg-[#25241F] text-[#FAF8F5] text-xs font-semibold hover:bg-[#1A1916] transition-all flex items-center justify-center gap-2 shadow-xs cursor-pointer group"
          >
            <Plus className="w-4 h-4 text-[#C5A878] group-hover:scale-110 transition-transform" />
            <span>New Chat Session</span>
          </button>
        </div>

        {/* Navigation Modes Switcher */}
        <div className="px-3 pt-3 pb-2 space-y-1 border-b border-[#E8E2D5]/70">
          <button
            onClick={() => {
              setCurrentView("chat");
              setMobileOpen(false);
            }}
            className={`w-full px-3 py-2 rounded-xl text-xs font-medium flex items-center justify-between transition-colors cursor-pointer ${
              currentView === "chat"
                ? "bg-[#EFE9DF] text-[#25241F] font-semibold"
                : "text-[#656056] hover:bg-[#F0EBE2]"
            }`}
          >
            <div className="flex items-center gap-2.5">
              <MessageSquare className="w-4 h-4 text-[#C5A878]" />
              <span>AI Chat Workspace</span>
            </div>
            {currentView === "chat" && <span className="w-1.5 h-1.5 rounded-full bg-[#B79A68]" />}
          </button>

          <button
            onClick={() => {
              setCurrentView("queue");
              setMobileOpen(false);
            }}
            className={`w-full px-3 py-2 rounded-xl text-xs font-medium flex items-center justify-between transition-colors cursor-pointer ${
              currentView === "queue"
                ? "bg-[#EFE9DF] text-[#25241F] font-semibold"
                : "text-[#656056] hover:bg-[#F0EBE2]"
            }`}
          >
            <div className="flex items-center gap-2.5">
              <UserCheck className="w-4 h-4 text-[#3E7B54]" />
              <span>Reviewer Queue</span>
            </div>
            {pendingReviewsCount > 0 ? (
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-[#FDF1EF] text-[#BD4C3D] border border-[#E8B6AF]">
                {pendingReviewsCount}
              </span>
            ) : (
              <span className="text-[10px] font-mono text-[#8C877B]">0</span>
            )}
          </button>

          <button
            onClick={() => {
              setCurrentView("compare");
              setMobileOpen(false);
            }}
            className={`w-full px-3 py-2 rounded-xl text-xs font-medium flex items-center justify-between transition-colors cursor-pointer ${
              currentView === "compare"
                ? "bg-[#EFE9DF] text-[#25241F] font-semibold"
                : "text-[#656056] hover:bg-[#F0EBE2]"
            }`}
          >
            <div className="flex items-center gap-2.5">
              <GitCompare className="w-4 h-4 text-[#C67D26]" />
              <span>Side-by-Side (B0 vs B3)</span>
            </div>
          </button>

          <button
            onClick={() => {
              setCurrentView("analytics");
              setMobileOpen(false);
            }}
            className={`w-full px-3 py-2 rounded-xl text-xs font-medium flex items-center justify-between transition-colors cursor-pointer ${
              currentView === "analytics"
                ? "bg-[#EFE9DF] text-[#25241F] font-semibold"
                : "text-[#656056] hover:bg-[#F0EBE2]"
            }`}
          >
            <div className="flex items-center gap-2.5">
              <BarChart3 className="w-4 h-4 text-[#777267]" />
              <span>Audit & Telemetry</span>
            </div>
          </button>
        </div>

        {/* Clinical Presets Drawer Toggle */}
        <div className="px-3 py-2 border-b border-[#E8E2D5]/70">
          <button
            onClick={() => setShowPresets(!showPresets)}
            className="w-full flex items-center justify-between text-xs text-[#8C7349] font-semibold py-1 px-1.5 rounded hover:bg-[#F0EBE2] transition-colors cursor-pointer"
          >
            <span className="flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Clinical Scenarios / Presets</span>
            </span>
            <ChevronRight
              className={`w-3.5 h-3.5 transition-transform duration-200 ${
                showPresets ? "rotate-90" : ""
              }`}
            />
          </button>

          {showPresets && (
            <div className="mt-2 space-y-1 animate-fade-in">
              {PRESETS.map((p) => (
                <button
                  key={p.key}
                  onClick={() => {
                    onSelectPreset(p);
                    setCurrentView("chat");
                    setMobileOpen(false);
                  }}
                  className="w-full text-left p-2 rounded-lg bg-[#FAF8F5] hover:bg-[#EFE9DF] border border-[#E8E2D5] text-xs transition-colors cursor-pointer group"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-[#292720] group-hover:text-[#8C7349]">
                      {p.label}
                    </span>
                    <span
                      className={`text-[9px] font-mono px-1.5 py-0.2 rounded ${
                        p.sim_level === "high"
                          ? "bg-[#EDF5F0] text-[#3E7B54]"
                          : p.sim_level === "medium"
                          ? "bg-[#FDF5EB] text-[#C67D26]"
                          : "bg-[#FDF1EF] text-[#BD4C3D]"
                      }`}
                    >
                      {p.sim_level}
                    </span>
                  </div>
                  <p className="text-[10px] text-[#777267] line-clamp-1 mt-0.5">{p.question}</p>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Sessions / Conversation History */}
        <div className="flex-1 overflow-y-auto px-3 py-2">
          {/* Search Bar */}
          <div className="relative mb-2.5">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-[#A8A296] pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search conversations..."
              className="w-full pl-8 pr-3 py-1.5 bg-[#FAF8F5] border border-[#E8E2D5] rounded-xl text-xs text-[#292720] placeholder-[#A8A296] focus:outline-none focus:ring-1 focus:ring-[#C5A878]"
            />
          </div>

          <div className="text-[10px] font-mono uppercase tracking-wider text-[#8C877B] px-1 mb-1.5">
            Conversation History ({filteredSessions.length})
          </div>

          <div className="space-y-1">
            {filteredSessions.length === 0 ? (
              <div className="py-6 text-center text-xs text-[#A8A296]">
                No matching sessions found.
              </div>
            ) : (
              filteredSessions.map((s) => {
                const isActive = s.id === currentSessionId && currentView === "chat";
                return (
                  <div
                    key={s.id}
                    onClick={() => {
                      onSelectSession(s.id);
                      setCurrentView("chat");
                      setMobileOpen(false);
                    }}
                    className={`group relative flex items-center justify-between p-2.5 rounded-xl text-xs cursor-pointer transition-all ${
                      isActive
                        ? "bg-[#EAE4D7] text-[#25241F] font-semibold shadow-2xs border border-[#D5CEBF]"
                        : "text-[#4A473E] hover:bg-[#F0EBE2] border border-transparent"
                    }`}
                  >
                    <div className="flex items-center gap-2 min-w-0 flex-1 pr-1">
                      <MessageSquare
                        className={`w-3.5 h-3.5 shrink-0 ${
                          isActive ? "text-[#8C7349]" : "text-[#A8A296]"
                        }`}
                      />
                      <div className="truncate">
                        <span className="block truncate">{s.title || "Clinical Inquiry"}</span>
                        <span className="text-[10px] text-[#8C877B] font-mono block">
                          {new Date(s.updatedAt).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </span>
                      </div>
                    </div>

                    {/* Delete Session button on hover */}
                    {sessions.length > 1 && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteSession(s.id);
                        }}
                        title="Delete conversation"
                        className="opacity-0 group-hover:opacity-100 p-1 rounded-md text-[#8C877B] hover:text-[#BD4C3D] hover:bg-[#FDF1EF] transition-all cursor-pointer"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Bottom User Profile & Settings Footer */}
        <div className="p-3 border-t border-[#E8E2D5] bg-[#FAF8F5]">
          <div className="flex items-center justify-between p-2 rounded-xl bg-[#FFFEFC] border border-[#E8E2D5]">
            <button
              onClick={onOpenProfile}
              className="flex items-center gap-2.5 min-w-0 text-left cursor-pointer flex-1"
            >
              <div className="w-8 h-8 rounded-full bg-[#25241F] text-[#C5A878] flex items-center justify-center font-bold text-xs shrink-0 shadow-2xs">
                {user?.name ? user.name.replace("Dr. ", "").charAt(0) : "U"}
              </div>
              <div className="truncate">
                <span className="text-xs font-semibold text-[#292720] block truncate">
                  {user?.name || "Clinician"}
                </span>
                <span className="text-[10px] text-[#8C877B] block truncate">
                  {user?.role || "Reviewer"}
                </span>
              </div>
            </button>

            <div className="flex items-center gap-1 shrink-0 ml-1">
              <button
                onClick={onOpenSettings}
                title="System Settings"
                className="p-1.5 rounded-lg text-[#777267] hover:text-[#292720] hover:bg-[#F0EBE2] transition-colors cursor-pointer"
              >
                <Settings className="w-4 h-4" />
              </button>
              <button
                onClick={logout}
                title="Sign Out"
                className="p-1.5 rounded-lg text-[#777267] hover:text-[#BD4C3D] hover:bg-[#FDF1EF] transition-colors cursor-pointer"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
