import { useState, useEffect } from "react";
import {
  Users,
  MessageSquare,
  Activity,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Search,
  Layers,
  Menu,
  ShieldAlert,
} from "lucide-react";
import { api } from "../lib/api";
import type { AdminUser, AdminStats, AdminConversation, RoutingLogItem } from "../types";

interface AdminDashboardViewProps {
  onToggleMobileSidebar: () => void;
}

export default function AdminDashboardView({ onToggleMobileSidebar }: AdminDashboardViewProps) {
  const [activeTab, setActiveTab] = useState<"overview" | "users" | "conversations" | "routing" | "reviews">("overview");
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [conversations, setConversations] = useState<AdminConversation[]>([]);
  const [routingLogs, setRoutingLogs] = useState<RoutingLogItem[]>([]);
  const [reviews, setReviews] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadAllAdminData = async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const [statsData, usersData, convsData, routingData, reviewsData] = await Promise.all([
        api.getAdminStats(),
        api.getAdminUsers(),
        api.getAdminConversations(),
        api.getRoutingLogs(150),
        api.getAdminReviews(150),
      ]);
      setStats(statsData);
      setUsers(usersData);
      setConversations(convsData);
      setRoutingLogs(routingData);
      setReviews(reviewsData);
    } catch (err: any) {
      console.error("Admin dashboard data fetch failed:", err);
      setErrorMessage(err.message || "Failed to load administrative records. Verify superuser credentials.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadAllAdminData();
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    loadAllAdminData();
  };

  // Filter users
  const filteredUsers = users.filter(
    (u) =>
      u.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      u.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      u.department.toLowerCase().includes(searchQuery.toLowerCase()) ||
      u.role.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Filter conversations
  const filteredConversations = conversations.filter(
    (c) =>
      c.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (c.user_email && c.user_email.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (c.user_name && c.user_name.toLowerCase().includes(searchQuery.toLowerCase())) ||
      c.subject.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Filter routing logs
  const filteredRoutingLogs = routingLogs.filter(
    (r) =>
      (r.question && r.question.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (r.query_id && r.query_id.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (r.selected_model && r.selected_model.toLowerCase().includes(searchQuery.toLowerCase())) ||
      r.routing_decision.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Filter reviews
  const filteredReviews = reviews.filter(
    (rev) =>
      (rev.reviewer_name && rev.reviewer_name.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (rev.query_id && rev.query_id.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (rev.decision && rev.decision.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (rev.notes && rev.notes.toLowerCase().includes(searchQuery.toLowerCase()))
  );

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
                System Administrator Console
              </h2>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold uppercase bg-[#F3EDE2] text-[#8C7349] border border-[#E0D5C1]">
                Superuser RBAC
              </span>
            </div>
            <p className="text-xs text-[#777267] hidden sm:block">
              Clinical AI Governance, User Audit, Routing Telemetry & Database Management
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="py-1.5 px-3 rounded-xl border border-[#E8E2D5] bg-[#FFFEFC] text-xs font-medium text-[#777267] hover:bg-[#FAF8F5] transition-colors flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-[#C5A878] ${refreshing ? "animate-spin" : ""}`} />
            <span className="hidden sm:inline">Refresh Data</span>
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 overflow-y-auto p-4 sm:p-8 space-y-6">
        {errorMessage && (
          <div className="p-4 rounded-2xl bg-[#FDF1EF] border border-[#E8B6AF] flex items-center gap-3 text-xs text-[#BD4C3D]">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Tab Navigation */}
        <div className="flex items-center gap-2 border-b border-[#E8E2D5] pb-2 overflow-x-auto">
          {[
            { id: "overview", label: "Executive Overview", icon: Activity },
            { id: "users", label: `User Directory (${users.length})`, icon: Users },
            { id: "conversations", label: `Conversations (${conversations.length})`, icon: MessageSquare },
            { id: "routing", label: `Routing Logs (${routingLogs.length})`, icon: Layers },
            { id: "reviews", label: `Human Reviews (${reviews.length})`, icon: CheckCircle2 },
          ].map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => {
                  setActiveTab(tab.id as any);
                  setSearchQuery("");
                }}
                className={`py-2 px-3.5 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all cursor-pointer whitespace-nowrap ${
                  active
                    ? "bg-[#25241F] text-[#FAF8F5] shadow-sm"
                    : "text-[#777267] hover:text-[#292720] hover:bg-[#EFE9DC]"
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${active ? "text-[#C5A878]" : "text-[#9E988A]"}`} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <RefreshCw className="w-8 h-8 text-[#C5A878] animate-spin mb-3" />
            <p className="text-sm font-semibold text-[#292720]">Loading Administrative Telemetry...</p>
            <p className="text-xs text-[#777267] mt-1 font-mono">Connecting to Cloud Database & Session Registry</p>
          </div>
        ) : (
          <>
            {/* OVERVIEW TAB */}
            {activeTab === "overview" && stats && (
              <div className="space-y-6">
                {/* Metric Cards Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="p-5 rounded-2xl bg-[#FFFEFC] border border-[#E8E2D5] shadow-xs">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[11px] font-semibold text-[#777267] uppercase tracking-wider">
                        Registered Accounts
                      </span>
                      <Users className="w-4 h-4 text-[#C5A878]" />
                    </div>
                    <div className="text-2xl font-bold font-heading text-[#292720]">{stats.total_users}</div>
                    <div className="text-[11px] text-[#3E7B54] font-medium mt-1">
                      {stats.active_users} active clinicians & reviewers
                    </div>
                  </div>

                  <div className="p-5 rounded-2xl bg-[#FFFEFC] border border-[#E8E2D5] shadow-xs">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[11px] font-semibold text-[#777267] uppercase tracking-wider">
                        Chat Inquiries
                      </span>
                      <MessageSquare className="w-4 h-4 text-[#C5A878]" />
                    </div>
                    <div className="text-2xl font-bold font-heading text-[#292720]">{stats.total_conversations}</div>
                    <div className="text-[11px] text-[#777267] font-medium mt-1">
                      {stats.total_messages} message exchanges persisted
                    </div>
                  </div>

                  <div className="p-5 rounded-2xl bg-[#FFFEFC] border border-[#E8E2D5] shadow-xs">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[11px] font-semibold text-[#777267] uppercase tracking-wider">
                        Routing Volume
                      </span>
                      <Layers className="w-4 h-4 text-[#C5A878]" />
                    </div>
                    <div className="text-2xl font-bold font-heading text-[#292720]">{stats.total_queries}</div>
                    <div className="text-[11px] text-[#777267] font-medium mt-1">
                      {stats.routes.direct} direct answers released
                    </div>
                  </div>

                  <div className="p-5 rounded-2xl bg-[#FFFEFC] border border-[#E8E2D5] shadow-xs">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[11px] font-semibold text-[#777267] uppercase tracking-wider">
                        Safety Catches
                      </span>
                      <ShieldAlert className="w-4 h-4 text-[#C67D26]" />
                    </div>
                    <div className="text-2xl font-bold font-heading text-[#C67D26]">{stats.high_risk_count}</div>
                    <div className="text-[11px] text-[#777267] font-medium mt-1">
                      {stats.routes.human} human review holds
                    </div>
                  </div>
                </div>

                {/* Sub-grid of detailed breakdowns */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Routing Decision Distribution */}
                  <div className="p-6 rounded-2xl bg-[#FFFEFC] border border-[#E8E2D5] shadow-xs">
                    <h3 className="text-sm font-bold text-[#292720] font-heading mb-4 flex items-center gap-2">
                      <Activity className="w-4 h-4 text-[#C5A878]" />
                      <span>Intelligent Routing Distribution</span>
                    </h3>
                    <div className="space-y-3">
                      <div>
                        <div className="flex justify-between text-xs font-semibold mb-1">
                          <span className="text-[#3E7B54]">Direct Answer (High Confidence &ge; 0.80)</span>
                          <span>{stats.routes.direct}</span>
                        </div>
                        <div className="w-full bg-[#EFE9DC] h-2 rounded-full overflow-hidden">
                          <div
                            className="bg-[#3E7B54] h-full rounded-full"
                            style={{
                              width: `${(stats.routes.direct / (stats.total_queries || 1)) * 100}%`,
                            }}
                          />
                        </div>
                      </div>

                      <div>
                        <div className="flex justify-between text-xs font-semibold mb-1">
                          <span className="text-[#C67D26]">Tier 2 Escalation (0.50 &le; Score &lt; 0.80)</span>
                          <span>{stats.routes.tier2}</span>
                        </div>
                        <div className="w-full bg-[#EFE9DC] h-2 rounded-full overflow-hidden">
                          <div
                            className="bg-[#C67D26] h-full rounded-full"
                            style={{
                              width: `${(stats.routes.tier2 / (stats.total_queries || 1)) * 100}%`,
                            }}
                          />
                        </div>
                      </div>

                      <div>
                        <div className="flex justify-between text-xs font-semibold mb-1">
                          <span className="text-[#BD4C3D]">Human Clinical Hold (&lt; 0.50 or High Risk)</span>
                          <span>{stats.routes.human}</span>
                        </div>
                        <div className="w-full bg-[#EFE9DC] h-2 rounded-full overflow-hidden">
                          <div
                            className="bg-[#BD4C3D] h-full rounded-full"
                            style={{
                              width: `${(stats.routes.human / (stats.total_queries || 1)) * 100}%`,
                            }}
                          />
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Clinical Reviews Breakdown */}
                  <div className="p-6 rounded-2xl bg-[#FFFEFC] border border-[#E8E2D5] shadow-xs">
                    <h3 className="text-sm font-bold text-[#292720] font-heading mb-4 flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-[#C5A878]" />
                      <span>Human Review Audit Status</span>
                    </h3>
                    <div className="grid grid-cols-2 gap-3 text-center">
                      <div className="p-3 rounded-xl bg-[#FAF8F5] border border-[#E8E2D5]">
                        <span className="text-[10px] font-mono uppercase text-[#777267] block">Pending Triage</span>
                        <span className="text-xl font-bold text-[#C67D26]">{stats.reviews.pending}</span>
                      </div>
                      <div className="p-3 rounded-xl bg-[#FAF8F5] border border-[#E8E2D5]">
                        <span className="text-[10px] font-mono uppercase text-[#777267] block">Approved</span>
                        <span className="text-xl font-bold text-[#3E7B54]">{stats.reviews.approved}</span>
                      </div>
                      <div className="p-3 rounded-xl bg-[#FAF8F5] border border-[#E8E2D5]">
                        <span className="text-[10px] font-mono uppercase text-[#777267] block">Clinician Corrected</span>
                        <span className="text-xl font-bold text-[#292720]">{stats.reviews.edited}</span>
                      </div>
                      <div className="p-3 rounded-xl bg-[#FAF8F5] border border-[#E8E2D5]">
                        <span className="text-[10px] font-mono uppercase text-[#777267] block">Rejected Refusal</span>
                        <span className="text-xl font-bold text-[#BD4C3D]">{stats.reviews.rejected}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* USERS TAB */}
            {activeTab === "users" && (
              <div className="space-y-4">
                {/* Search */}
                <div className="relative">
                  <Search className="w-4 h-4 absolute left-3.5 top-3 text-[#9E988A]" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search users by name, email, department, or role..."
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-[#E8E2D5] bg-[#FFFEFC] text-xs text-[#292720] placeholder-[#9E988A] focus:outline-none focus:ring-2 focus:ring-[#C5A878]/50"
                  />
                </div>

                {/* Table */}
                <div className="rounded-2xl border border-[#E8E2D5] bg-[#FFFEFC] overflow-hidden shadow-xs">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-[#FAF8F5] border-b border-[#E8E2D5] text-[#777267] uppercase font-mono text-[10px]">
                        <tr>
                          <th className="py-3 px-4">Clinician / User</th>
                          <th className="py-3 px-4">Email</th>
                          <th className="py-3 px-4">Role</th>
                          <th className="py-3 px-4">Department</th>
                          <th className="py-3 px-4">Status</th>
                          <th className="py-3 px-4">Registered Date</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#F1ECE2]">
                        {filteredUsers.map((u) => (
                          <tr key={u.id} className="hover:bg-[#FDFCF9] transition-colors">
                            <td className="py-3 px-4 font-semibold text-[#292720] flex items-center gap-2">
                              <div className="w-7 h-7 rounded-lg bg-[#25241F] text-[#C5A878] flex items-center justify-center font-bold text-xs">
                                {u.name.charAt(0)}
                              </div>
                              <span>{u.name}</span>
                            </td>
                            <td className="py-3 px-4 text-[#777267] font-mono">{u.email}</td>
                            <td className="py-3 px-4">
                              <span
                                className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase ${
                                  u.role === "admin"
                                    ? "bg-[#25241F] text-[#C5A878] border border-[#C5A878]/40"
                                    : "bg-[#EFE9DC] text-[#777267]"
                                }`}
                              >
                                {u.role}
                              </span>
                            </td>
                            <td className="py-3 px-4 text-[#4A473E]">{u.department}</td>
                            <td className="py-3 px-4">
                              <span className="inline-flex items-center gap-1.5 text-[#3E7B54] font-semibold text-[11px]">
                                <span className="w-1.5 h-1.5 rounded-full bg-[#3E7B54]" />
                                Active
                              </span>
                            </td>
                            <td className="py-3 px-4 text-[#777267] font-mono">
                              {new Date(u.created_at).toLocaleDateString()}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {/* CONVERSATIONS TAB */}
            {activeTab === "conversations" && (
              <div className="space-y-4">
                <div className="relative">
                  <Search className="w-4 h-4 absolute left-3.5 top-3 text-[#9E988A]" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search conversations by title, user email, or medical subject..."
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-[#E8E2D5] bg-[#FFFEFC] text-xs text-[#292720] placeholder-[#9E988A] focus:outline-none focus:ring-2 focus:ring-[#C5A878]/50"
                  />
                </div>

                <div className="rounded-2xl border border-[#E8E2D5] bg-[#FFFEFC] overflow-hidden shadow-xs">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-[#FAF8F5] border-b border-[#E8E2D5] text-[#777267] uppercase font-mono text-[10px]">
                        <tr>
                          <th className="py-3 px-4">Conversation ID</th>
                          <th className="py-3 px-4">Title</th>
                          <th className="py-3 px-4">Specialty</th>
                          <th className="py-3 px-4">User Attribution</th>
                          <th className="py-3 px-4">Messages</th>
                          <th className="py-3 px-4">Last Activity</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#F1ECE2]">
                        {filteredConversations.map((c) => (
                          <tr key={c.id} className="hover:bg-[#FDFCF9] transition-colors">
                            <td className="py-3 px-4 font-mono text-[#777267] text-[11px]">{c.id}</td>
                            <td className="py-3 px-4 font-semibold text-[#292720]">{c.title}</td>
                            <td className="py-3 px-4">
                              <span className="px-2 py-0.5 rounded bg-[#FAF8F5] border border-[#E8E2D5] text-[#777267] text-[11px]">
                                {c.subject}
                              </span>
                            </td>
                            <td className="py-3 px-4 text-[#4A473E]">
                              {c.user_name || c.user_email ? (
                                <div>
                                  <div className="font-semibold">{c.user_name || "Clinician"}</div>
                                  <div className="text-[10px] text-[#777267] font-mono">{c.user_email}</div>
                                </div>
                              ) : (
                                <span className="text-[#9E988A] italic">Unassigned / System</span>
                              )}
                            </td>
                            <td className="py-3 px-4 font-mono text-[#292720]">{c.message_count}</td>
                            <td className="py-3 px-4 text-[#777267] font-mono text-[11px]">
                              {new Date(c.updated_at).toLocaleString()}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {/* ROUTING LOGS TAB */}
            {activeTab === "routing" && (
              <div className="space-y-4">
                <div className="relative">
                  <Search className="w-4 h-4 absolute left-3.5 top-3 text-[#9E988A]" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search logs by query text, query ID, model, or decision..."
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-[#E8E2D5] bg-[#FFFEFC] text-xs text-[#292720] placeholder-[#9E988A] focus:outline-none focus:ring-2 focus:ring-[#C5A878]/50"
                  />
                </div>

                <div className="rounded-2xl border border-[#E8E2D5] bg-[#FFFEFC] overflow-hidden shadow-xs">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-[#FAF8F5] border-b border-[#E8E2D5] text-[#777267] uppercase font-mono text-[10px]">
                        <tr>
                          <th className="py-3 px-4">Query ID</th>
                          <th className="py-3 px-4">Medical Prompt</th>
                          <th className="py-3 px-4">Score</th>
                          <th className="py-3 px-4">Routing Decision</th>
                          <th className="py-3 px-4">Model Used</th>
                          <th className="py-3 px-4">Risk Flag</th>
                          <th className="py-3 px-4">Timestamp</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#F1ECE2]">
                        {filteredRoutingLogs.map((log) => (
                          <tr key={log.id} className="hover:bg-[#FDFCF9] transition-colors">
                            <td className="py-3 px-4 font-mono text-[#777267] text-[11px]">{log.query_id || log.id}</td>
                            <td className="py-3 px-4 text-[#292720] max-w-xs truncate" title={log.question || ""}>
                              {log.question || "Chat interaction message"}
                            </td>
                            <td className="py-3 px-4 font-mono font-bold text-[#292720]">
                              {log.confidence_score !== null ? (log.confidence_score * 100).toFixed(1) + "%" : "N/A"}
                            </td>
                            <td className="py-3 px-4">
                              <span
                                className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase ${
                                  log.routing_decision === "direct"
                                    ? "bg-[#EBF5EF] text-[#3E7B54]"
                                    : log.routing_decision === "tier2"
                                    ? "bg-[#FDF6EC] text-[#C67D26]"
                                    : "bg-[#FDF1EF] text-[#BD4C3D]"
                                }`}
                              >
                                {log.routing_decision}
                              </span>
                            </td>
                            <td className="py-3 px-4 text-[#777267] font-mono text-[11px]">
                              {log.selected_model || "tier1"}
                            </td>
                            <td className="py-3 px-4">
                              {log.is_high_risk ? (
                                <span className="inline-flex items-center gap-1 text-[#BD4C3D] font-semibold text-[10px] uppercase">
                                  <ShieldAlert className="w-3 h-3" />
                                  High Risk
                                </span>
                              ) : (
                                <span className="text-[#3E7B54] font-medium text-[10px]">Standard</span>
                              )}
                            </td>
                            <td className="py-3 px-4 text-[#777267] font-mono text-[11px]">
                              {new Date(log.created_at).toLocaleString()}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {/* REVIEWS TAB */}
            {activeTab === "reviews" && (
              <div className="space-y-4">
                <div className="relative">
                  <Search className="w-4 h-4 absolute left-3.5 top-3 text-[#9E988A]" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search reviews by reviewer name, case ID, decision, or audit notes..."
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-[#E8E2D5] bg-[#FFFEFC] text-xs text-[#292720] placeholder-[#9E988A] focus:outline-none focus:ring-2 focus:ring-[#C5A878]/50"
                  />
                </div>

                <div className="rounded-2xl border border-[#E8E2D5] bg-[#FFFEFC] overflow-hidden shadow-xs">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-[#FAF8F5] border-b border-[#E8E2D5] text-[#777267] uppercase font-mono text-[10px]">
                        <tr>
                          <th className="py-3 px-4">Review ID</th>
                          <th className="py-3 px-4">Case ID</th>
                          <th className="py-3 px-4">Reviewer</th>
                          <th className="py-3 px-4">Decision</th>
                          <th className="py-3 px-4">Corrected Output</th>
                          <th className="py-3 px-4">Clinical Notes</th>
                          <th className="py-3 px-4">Review Date</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#F1ECE2]">
                        {filteredReviews.map((rev) => (
                          <tr key={rev.id} className="hover:bg-[#FDFCF9] transition-colors">
                            <td className="py-3 px-4 font-mono text-[#777267] text-[11px]">{rev.id}</td>
                            <td className="py-3 px-4 font-mono font-bold text-[#292720]">{rev.query_id}</td>
                            <td className="py-3 px-4 font-semibold text-[#292720]">{rev.reviewer_name || "Dr. Sarah Chen"}</td>
                            <td className="py-3 px-4">
                              <span
                                className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase ${
                                  rev.decision === "approved"
                                    ? "bg-[#EBF5EF] text-[#3E7B54]"
                                    : rev.decision === "edited"
                                    ? "bg-[#FDF6EC] text-[#C67D26]"
                                    : "bg-[#FDF1EF] text-[#BD4C3D]"
                                }`}
                              >
                                {rev.decision}
                              </span>
                            </td>
                            <td className="py-3 px-4 text-[#4A473E] max-w-xs truncate" title={rev.corrected_response || ""}>
                              {rev.corrected_response || <span className="text-[#9E988A] italic">Unmodified AI Draft</span>}
                            </td>
                            <td className="py-3 px-4 text-[#777267] max-w-xs truncate" title={rev.notes || ""}>
                              {rev.notes || "—"}
                            </td>
                            <td className="py-3 px-4 text-[#777267] font-mono text-[11px]">
                              {new Date(rev.created_at).toLocaleString()}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
