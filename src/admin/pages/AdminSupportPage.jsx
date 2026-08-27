import React, { useState, useMemo, useRef, useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import {
  LifeBuoy,
  Search,
  Filter,
  CheckCircle2,
  Clock,
  AlertCircle,
  AlertTriangle,
  Flame,
  User,
  Mail,
  Calendar,
  MessageSquare,
  Shield,
  Lock,
  Eye,
  Send,
  UserCheck,
  UserPlus,
  Paperclip,
  X,
  Sparkles,
  ArrowLeft,
  RefreshCw,
  FileText,
  BadgeCheck,
  ChevronDown,
  Layers,
  Inbox,
  ExternalLink,
  ShieldAlert,
  StickyNote,
  BookOpen,
} from "lucide-react";
import { toast } from "sonner";

import {
  useAdminSupportTickets,
  useAdminSupportTicket,
  useAdminReplySupportTicket,
  useAdminUpdateSupportTicketStatus,
  useAdminAssignSupportTicket,
  useAdminAddInternalNote,
  useAdminUpdateSupportTicketPriority,
  useAdminUsers,
} from "@/admin/adminApi";
import AdminFaqManager from "@/admin/components/AdminFaqManager";
import {
  PageHeading,
  EasyXCard,
  EasyXButton,
  EasyXLoader,
  EasyXEmptyState,
  EasyXModal,
} from "@/design/EasyX";
import {
  SupportStatusBadge,
  SupportPriorityBadge,
  SupportCategoryBadge,
} from "@/user/components/SupportStatusBadge";
import SupportAttachmentViewer from "@/shared/components/SupportAttachmentViewer";
import SupportAttachmentUploader, { uploadSupportFiles } from "@/shared/components/SupportAttachmentUploader";

dayjs.extend(relativeTime);

const CATEGORIES = [
  { id: "", label: "All Categories" },
  { id: "ACCOUNT", label: "Account" },
  { id: "LOGIN", label: "Login & Access" },
  { id: "DEPOSIT", label: "Deposit" },
  { id: "INVESTMENT", label: "Investment" },
  { id: "KYC", label: "KYC Verification" },
  { id: "WITHDRAWAL", label: "Withdrawal" },
  { id: "WALLET", label: "Wallet & Funds" },
  { id: "REFERRAL", label: "Referrals" },
  { id: "TECHNICAL", label: "Technical" },
  { id: "OTHER", label: "Other" },
];

const PRIORITIES = [
  { id: "", label: "All Priorities" },
  { id: "URGENT", label: "Urgent" },
  { id: "HIGH", label: "High" },
  { id: "NORMAL", label: "Normal" },
  { id: "LOW", label: "Low" },
];

const STATUS_TABS = [
  { id: "", label: "All Tickets" },
  { id: "OPEN", label: "Open" },
  { id: "WAITING_FOR_ADMIN", label: "Waiting for Staff" },
  { id: "WAITING_FOR_USER", label: "Waiting for User" },
  { id: "IN_PROGRESS", label: "In Progress" },
  { id: "RESOLVED", label: "Resolved" },
  { id: "CLOSED", label: "Closed" },
];

export default function AdminSupportPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  // Filters & State
  const [activeSection, setActiveSection] = useState(
    searchParams.get("section") === "faq" ? "FAQ" : "TICKETS"
  );
  const initialTicketId = searchParams.get("ticket") || null;
  const [selectedTicketId, setSelectedTicketId] = useState(initialTicketId);
  const [statusFilter, setStatusFilter] = useState(searchParams.get("status") || "");
  const [categoryFilter, setCategoryFilter] = useState(searchParams.get("category") || "");
  const [priorityFilter, setPriorityFilter] = useState(searchParams.get("priority") || "");
  const [assignedAdminFilter, setAssignedAdminFilter] = useState(searchParams.get("assigned") || "");
  const [searchQuery, setSearchQuery] = useState(searchParams.get("q") || "");
  const [dateFilter, setDateFilter] = useState("ALL"); // ALL, TODAY, 7D, 30D

  // Switch section between Tickets and FAQ Manager
  const handleSwitchSection = (section) => {
    setActiveSection(section);
    const newParams = new URLSearchParams(searchParams);
    if (section === "FAQ") {
      newParams.set("section", "faq");
    } else {
      newParams.delete("section");
    }
    setSearchParams(newParams, { replace: true });
  };

  // Sync selectedTicketId with URL
  const handleSelectTicket = (id) => {
    setSelectedTicketId(id);
    const newParams = new URLSearchParams(searchParams);
    if (id) {
      newParams.set("ticket", id);
    } else {
      newParams.delete("ticket");
    }
    setSearchParams(newParams, { replace: true });
  };

  // Queries
  const {
    data: ticketData,
    isLoading: isListLoading,
    isRefetching,
    refetch,
  } = useAdminSupportTickets({
    status: statusFilter || undefined,
    category: categoryFilter || undefined,
    priority: priorityFilter || undefined,
    assigned_admin_id: assignedAdminFilter || undefined,
    search: searchQuery.trim() || undefined,
  });

  const { data: usersData } = useAdminUsers();
  const adminUsers = useMemo(() => {
    if (!usersData) return [];
    const list = Array.isArray(usersData) ? usersData : usersData.users || [];
    return list.filter((u) => u.role === "admin");
  }, [usersData]);

  const rawTickets = ticketData?.tickets || [];
  const summary = ticketData?.summary || {};

  // Client-side date filter if selected
  const filteredTickets = useMemo(() => {
    let result = rawTickets;
    if (dateFilter === "TODAY") {
      const today = dayjs().startOf("day");
      result = result.filter((t) => dayjs(t.created_at).isAfter(today));
    } else if (dateFilter === "7D") {
      const weekAgo = dayjs().subtract(7, "day");
      result = result.filter((t) => dayjs(t.created_at).isAfter(weekAgo));
    } else if (dateFilter === "30D") {
      const monthAgo = dayjs().subtract(30, "day");
      result = result.filter((t) => dayjs(t.created_at).isAfter(monthAgo));
    }
    return result;
  }, [rawTickets, dateFilter]);

  // Key metrics calculation
  const metrics = useMemo(() => {
    const total = summary.TOTAL || rawTickets.length;
    const openCount = summary.OPEN || 0;
    const urgentCount = rawTickets.filter((t) => (t.priority === "URGENT" || t.priority === "HIGH") && t.status !== "CLOSED" && t.status !== "RESOLVED").length;
    const waitingAdmin = summary.WAITING_FOR_ADMIN || 0;
    const waitingUser = summary.WAITING_FOR_USER || 0;
    
    // Resolved today
    const startOfToday = dayjs().startOf("day");
    const resolvedToday = rawTickets.filter((t) => t.resolved_at && dayjs(t.resolved_at).isAfter(startOfToday)).length;

    return {
      total,
      open: openCount,
      urgent: urgentCount,
      waitingAdmin,
      waitingUser,
      resolvedToday,
    };
  }, [summary, rawTickets]);

  return (
    <div id="admin-support-root" className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <PageHeading
            title="Support Center"
            description="Manage user tickets, prioritize urgent requests, reply to users, and maintain the Help Center FAQ knowledge base."
          />
        </div>
        <div className="flex items-center gap-2">
          {activeSection === "TICKETS" && (
            <button
              id="btn-refresh-tickets"
              onClick={() => refetch()}
              disabled={isRefetching}
              className="inline-flex items-center gap-2 px-3.5 py-2 rounded-ex-ctrl bg-white/5 hover:bg-white/10 text-ex-text border border-white/10 text-xs font-semibold transition disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isRefetching ? "animate-spin text-ex-primary" : ""}`} />
              Refresh Queue
            </button>
          )}
        </div>
      </div>

      {/* Top Section Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-white/10 pb-3">
        <button
          onClick={() => handleSwitchSection("TICKETS")}
          className={`flex items-center gap-2 px-4 py-2 rounded-ex-ctrl text-xs font-bold transition ${
            activeSection === "TICKETS"
              ? "bg-ex-primary text-ex-ink shadow-sm"
              : "bg-white/5 text-ex-muted hover:bg-white/10 hover:text-white"
          }`}
          data-testid="admin-tab-tickets"
        >
          <LifeBuoy className="h-4 w-4" />
          <span>Support Tickets Queue</span>
          {metrics.open > 0 && (
            <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-extrabold ${
              activeSection === "TICKETS" ? "bg-black/20 text-ex-ink" : "bg-sky-500/20 text-sky-300"
            }`}>
              {metrics.open}
            </span>
          )}
        </button>

        <button
          onClick={() => handleSwitchSection("FAQ")}
          className={`flex items-center gap-2 px-4 py-2 rounded-ex-ctrl text-xs font-bold transition ${
            activeSection === "FAQ"
              ? "bg-ex-primary text-ex-ink shadow-sm"
              : "bg-white/5 text-ex-muted hover:bg-white/10 hover:text-white"
          }`}
          data-testid="admin-tab-faqs"
        >
          <BookOpen className="h-4 w-4" />
          <span>Help Center & FAQ Manager</span>
        </button>
      </div>

      {/* FAQ KNOWLEDGE BASE MANAGER */}
      {activeSection === "FAQ" && (
        <AdminFaqManager />
      )}

      {/* TICKETS MANAGEMENT SECTION */}
      {activeSection === "TICKETS" && (
        <>
          {/* KPI Stats Dashboard */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div
          onClick={() => setStatusFilter("OPEN")}
          className={`cursor-pointer rounded-ex-surface p-3.5 border transition ${
            statusFilter === "OPEN" ? "bg-sky-500/10 border-sky-500/40" : "bg-white/[0.03] border-white/8 hover:bg-white/[0.06]"
          }`}
        >
          <div className="flex items-center justify-between text-xs text-sky-400 font-medium mb-1">
            <span>Open Tickets</span>
            <LifeBuoy className="h-4 w-4" />
          </div>
          <div className="text-xl sm:text-2xl font-bold text-white tracking-tight">{metrics.open}</div>
          <div className="text-[11px] text-white/50 mt-0.5">Awaiting initial triage</div>
        </div>

        <div
          onClick={() => setPriorityFilter(priorityFilter === "URGENT" ? "" : "URGENT")}
          className={`cursor-pointer rounded-ex-surface p-3.5 border transition ${
            priorityFilter === "URGENT" ? "bg-red-500/15 border-red-500/40" : "bg-white/[0.03] border-white/8 hover:bg-white/[0.06]"
          }`}
        >
          <div className="flex items-center justify-between text-xs text-red-400 font-medium mb-1">
            <span>High & Urgent</span>
            <Flame className="h-4 w-4" />
          </div>
          <div className="text-xl sm:text-2xl font-bold text-red-300 tracking-tight">{metrics.urgent}</div>
          <div className="text-[11px] text-white/50 mt-0.5">Critical attention</div>
        </div>

        <div
          onClick={() => setStatusFilter("WAITING_FOR_ADMIN")}
          className={`cursor-pointer rounded-ex-surface p-3.5 border transition ${
            statusFilter === "WAITING_FOR_ADMIN" ? "bg-cyan-500/15 border-cyan-500/40" : "bg-white/[0.03] border-white/8 hover:bg-white/[0.06]"
          }`}
        >
          <div className="flex items-center justify-between text-xs text-cyan-400 font-medium mb-1">
            <span>Waiting for Staff</span>
            <Clock className="h-4 w-4" />
          </div>
          <div className="text-xl sm:text-2xl font-bold text-cyan-300 tracking-tight">{metrics.waitingAdmin}</div>
          <div className="text-[11px] text-white/50 mt-0.5">Requires response</div>
        </div>

        <div
          onClick={() => setStatusFilter("WAITING_FOR_USER")}
          className={`cursor-pointer rounded-ex-surface p-3.5 border transition ${
            statusFilter === "WAITING_FOR_USER" ? "bg-purple-500/15 border-purple-500/40" : "bg-white/[0.03] border-white/8 hover:bg-white/[0.06]"
          }`}
        >
          <div className="flex items-center justify-between text-xs text-purple-400 font-medium mb-1">
            <span>Waiting for User</span>
            <User className="h-4 w-4" />
          </div>
          <div className="text-xl sm:text-2xl font-bold text-purple-300 tracking-tight">{metrics.waitingUser}</div>
          <div className="text-[11px] text-white/50 mt-0.5">Awaiting customer reply</div>
        </div>

        <div
          onClick={() => setStatusFilter("RESOLVED")}
          className={`cursor-pointer rounded-ex-surface p-3.5 border transition ${
            statusFilter === "RESOLVED" ? "bg-emerald-500/15 border-emerald-500/40" : "bg-white/[0.03] border-white/8 hover:bg-white/[0.06]"
          }`}
        >
          <div className="flex items-center justify-between text-xs text-emerald-400 font-medium mb-1">
            <span>Resolved Today</span>
            <CheckCircle2 className="h-4 w-4" />
          </div>
          <div className="text-xl sm:text-2xl font-bold text-emerald-300 tracking-tight">{metrics.resolvedToday}</div>
          <div className="text-[11px] text-white/50 mt-0.5">Completed today</div>
        </div>

        <div
          onClick={() => {
            setStatusFilter("");
            setPriorityFilter("");
            setCategoryFilter("");
            setAssignedAdminFilter("");
          }}
          className={`cursor-pointer rounded-ex-surface p-3.5 border transition ${
            !statusFilter && !priorityFilter && !categoryFilter && !assignedAdminFilter
              ? "bg-white/10 border-white/30"
              : "bg-white/[0.03] border-white/8 hover:bg-white/[0.06]"
          }`}
        >
          <div className="flex items-center justify-between text-xs text-white/70 font-medium mb-1">
            <span>Total Tickets</span>
            <Layers className="h-4 w-4" />
          </div>
          <div className="text-xl sm:text-2xl font-bold text-white tracking-tight">{metrics.total}</div>
          <div className="text-[11px] text-white/50 mt-0.5">Platform lifetime</div>
        </div>
      </div>

      {/* Main Support Area: Split View or Detail Modal */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Ticket List Column (Full width or left column) */}
        <div className={`space-y-4 ${selectedTicketId ? "lg:col-span-5 xl:col-span-5" : "lg:col-span-12"}`}>
          <EasyXCard className="p-4 sm:p-5 space-y-4">
            {/* Search & Main Status Tabs */}
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1">
                <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-white/40" />
                <input
                  id="input-support-search"
                  type="text"
                  placeholder="Search by Ticket ID, User name, Email..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-ex-ctrl pl-10 pr-9 py-2 text-sm text-white placeholder:text-white/40 focus:outline-none focus:border-ex-primary transition"
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery("")}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-white/40 hover:text-white"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>

              {/* Date Filter */}
              <div className="flex items-center gap-1.5 shrink-0">
                <select
                  id="select-date-filter"
                  value={dateFilter}
                  onChange={(e) => setDateFilter(e.target.value)}
                  className="bg-white/5 border border-white/10 rounded-ex-ctrl px-3 py-2 text-xs text-white/80 focus:outline-none focus:border-ex-primary"
                >
                  <option value="ALL" className="bg-[#12111c] text-white">All Time</option>
                  <option value="TODAY" className="bg-[#12111c] text-white">Today</option>
                  <option value="7D" className="bg-[#12111c] text-white">Last 7 Days</option>
                  <option value="30D" className="bg-[#12111c] text-white">Last 30 Days</option>
                </select>
              </div>
            </div>

            {/* Status Tabs Bar */}
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs border-b border-white/8 scrollbar-none">
              {STATUS_TABS.map((tab) => {
                const isActive = statusFilter === tab.id;
                return (
                  <button
                    key={tab.id}
                    id={`tab-status-${tab.id || "all"}`}
                    onClick={() => setStatusFilter(tab.id)}
                    className={`whitespace-nowrap px-3 py-1.5 rounded-ex-ctrl font-medium transition ${
                      isActive
                        ? "bg-ex-primary text-white shadow-sm"
                        : "text-white/60 hover:text-white hover:bg-white/5"
                    }`}
                  >
                    {tab.label}
                  </button>
                );
              })}
            </div>

            {/* Dropdown Filters (Category, Priority, Assigned Admin) */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-1">
              <div>
                <label className="block text-[11px] text-white/40 mb-1 font-medium">Category</label>
                <select
                  id="select-category-filter"
                  value={categoryFilter}
                  onChange={(e) => setCategoryFilter(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-ex-ctrl px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-ex-primary"
                >
                  {CATEGORIES.map((c) => (
                    <option key={c.id} value={c.id} className="bg-[#12111c] text-white">
                      {c.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[11px] text-white/40 mb-1 font-medium">Priority</label>
                <select
                  id="select-priority-filter"
                  value={priorityFilter}
                  onChange={(e) => setPriorityFilter(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-ex-ctrl px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-ex-primary"
                >
                  {PRIORITIES.map((p) => (
                    <option key={p.id} value={p.id} className="bg-[#12111c] text-white">
                      {p.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[11px] text-white/40 mb-1 font-medium">Assigned Admin</label>
                <select
                  id="select-assigned-admin-filter"
                  value={assignedAdminFilter}
                  onChange={(e) => setAssignedAdminFilter(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-ex-ctrl px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-ex-primary"
                >
                  <option value="" className="bg-[#12111c] text-white">All Staff / Unassigned</option>
                  {adminUsers.map((adm) => (
                    <option key={adm.id} value={adm.id} className="bg-[#12111c] text-white">
                      {adm.name || adm.email}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </EasyXCard>

          {/* Ticket Queue List */}
          <div className="space-y-2.5">
            {isListLoading ? (
              <div className="py-16 text-center">
                <EasyXLoader text="Loading support queue..." />
              </div>
            ) : filteredTickets.length === 0 ? (
              <EasyXCard className="p-8 text-center">
                <EasyXEmptyState
                  icon={Inbox}
                  title="No Support Tickets Found"
                  description="No tickets match the selected filters or search parameters."
                  action={
                    (statusFilter || categoryFilter || priorityFilter || assignedAdminFilter || searchQuery) && (
                      <EasyXButton
                        variant="ghost"
                        onClick={() => {
                          setStatusFilter("");
                          setCategoryFilter("");
                          setPriorityFilter("");
                          setAssignedAdminFilter("");
                          setSearchQuery("");
                          setDateFilter("ALL");
                        }}
                      >
                        Reset All Filters
                      </EasyXButton>
                    )
                  }
                />
              </EasyXCard>
            ) : (
              filteredTickets.map((ticket) => {
                const isSelected = selectedTicketId === ticket.id;
                const hasUnread = Boolean(ticket.unread_user_messages_count && ticket.unread_user_messages_count > 0);

                return (
                  <div
                    key={ticket.id}
                    id={`ticket-card-${ticket.id}`}
                    onClick={() => handleSelectTicket(ticket.id)}
                    className={`cursor-pointer rounded-ex-surface p-4 border transition ${
                      isSelected
                        ? "bg-ex-primary/10 border-ex-primary/50 shadow-md ring-1 ring-ex-primary/30"
                        : "bg-white/[0.03] border-white/8 hover:bg-white/[0.06] hover:border-white/15"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-mono text-xs font-bold text-ex-lav-300">
                          #{ticket.id.slice(-6).toUpperCase()}
                        </span>
                        <SupportStatusBadge status={ticket.status} />
                        <SupportPriorityBadge priority={ticket.priority} />
                        <SupportCategoryBadge category={ticket.category} />
                      </div>

                      <div className="text-[11px] text-white/40 shrink-0">
                        {dayjs(ticket.last_activity_at || ticket.updated_at).fromNow()}
                      </div>
                    </div>

                    <h3 className="text-sm font-semibold text-white tracking-tight line-clamp-1 mb-1.5">
                      {ticket.subject}
                    </h3>

                    {/* Preview of last message or description */}
                    {ticket.last_message && (
                      <p className="text-xs text-white/60 line-clamp-2 mb-3 bg-black/20 rounded-md p-2 border border-white/5">
                        <span className="font-medium text-white/80">
                          {ticket.last_message.sender_name || ticket.last_message.sender_type}:
                        </span>{" "}
                        {ticket.last_message.message}
                      </p>
                    )}

                    <div className="flex items-center justify-between pt-2 border-t border-white/5 text-[11px] text-white/50">
                      <div className="flex items-center gap-2 truncate">
                        <span className="font-medium text-white/80 truncate">
                          {ticket.user_name || ticket.user_email || "User"}
                        </span>
                        {ticket.user_email && (
                          <span className="text-white/40 truncate hidden sm:inline">
                            ({ticket.user_email})
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-3 shrink-0">
                        {ticket.assigned_admin_name ? (
                          <span className="inline-flex items-center gap-1 text-emerald-400">
                            <UserCheck className="h-3 w-3" />
                            {ticket.assigned_admin_name.split(" ")[0]}
                          </span>
                        ) : (
                          <span className="text-amber-400/80 italic">Unassigned</span>
                        )}

                        <span className="inline-flex items-center gap-1 text-white/40">
                          <MessageSquare className="h-3 w-3" />
                          {ticket.message_count || 1}
                        </span>

                        {hasUnread && (
                          <span className="px-1.5 py-0.2 rounded-full text-[10px] font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                            {ticket.unread_user_messages_count} new
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Ticket Details & Interaction Workspace Column */}
        {selectedTicketId ? (
          <div className="lg:col-span-7 xl:col-span-7 sticky top-4">
            <AdminTicketDetailWorkspace
              ticketId={selectedTicketId}
              adminUsers={adminUsers}
              onClose={() => handleSelectTicket(null)}
            />
          </div>
        ) : (
          <div className="hidden lg:flex lg:col-span-7 xl:col-span-7 rounded-ex-surface border border-white/8 bg-white/[0.02] p-12 min-h-[480px] flex-col items-center justify-center text-center">
            <div className="h-16 w-16 rounded-full bg-white/5 border border-white/10 grid place-items-center mb-4 text-white/40">
              <LifeBuoy className="h-8 w-8" />
            </div>
            <h3 className="text-base font-bold text-white mb-1">Select a Ticket from the Queue</h3>
            <p className="text-xs text-white/50 max-w-sm">
              Click on any support ticket from the list on the left to inspect user identity details, full communication history, and submit replies or internal notes.
            </p>
          </div>
        )}
      </div>
        </>
      )}
    </div>
  );
}

/**
 * Admin Ticket Detail Workspace Component
 */
function AdminTicketDetailWorkspace({ ticketId, adminUsers, onClose }) {
  const { data, isLoading, isError, refetch } = useAdminSupportTicket(ticketId);
  const replyMutation = useAdminReplySupportTicket();
  const statusMutation = useAdminUpdateSupportTicketStatus();
  const assignMutation = useAdminAssignSupportTicket();
  const internalNoteMutation = useAdminAddInternalNote();
  const priorityMutation = useAdminUpdateSupportTicketPriority();

  // Active form state
  const [activeTab, setActiveTab] = useState("REPLY"); // "REPLY" | "INTERNAL_NOTE"
  const [replyMessage, setReplyMessage] = useState("");
  const [adminAttachments, setAdminAttachments] = useState([]);
  const [isUploadingAttachments, setIsUploadingAttachments] = useState(false);
  const [nextStatus, setNextStatus] = useState("WAITING_FOR_USER");
  const [internalNote, setInternalNote] = useState("");
  const [statusChangeModalOpen, setStatusChangeModalOpen] = useState(false);
  const [targetStatus, setTargetStatus] = useState("RESOLVED");
  const [statusReason, setStatusReason] = useState("");

  const messagesEndRef = useRef(null);

  const ticket = data?.ticket;
  const messages = data?.messages || [];
  const user = data?.user;

  // Scroll to bottom when messages update
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages.length]);

  if (isLoading) {
    return (
      <EasyXCard className="p-8 text-center min-h-[400px] flex items-center justify-center">
        <EasyXLoader text="Loading ticket details & history..." />
      </EasyXCard>
    );
  }

  if (isError || !ticket) {
    return (
      <EasyXCard className="p-8 text-center space-y-4">
        <AlertCircle className="h-10 w-10 text-red-400 mx-auto" />
        <h3 className="text-base font-bold text-white">Ticket Not Found</h3>
        <p className="text-xs text-white/50">This support ticket could not be loaded or was removed.</p>
        <EasyXButton variant="ghost" onClick={onClose}>
          Return to Queue
        </EasyXButton>
      </EasyXCard>
    );
  }

  // Handle Admin Public Reply
  const handleSubmitReply = async (e) => {
    e.preventDefault();
    if (!replyMessage.trim() && adminAttachments.length === 0) {
      toast.error("Reply message or screenshot attachment is required.");
      return;
    }

    try {
      setIsUploadingAttachments(true);
      let uploadedAttachmentIds = [];

      if (adminAttachments.length > 0) {
        const rawFiles = adminAttachments.map((a) => a.rawFile).filter(Boolean);
        if (rawFiles.length > 0) {
          const uploaded = await uploadSupportFiles(rawFiles, true);
          uploadedAttachmentIds = uploaded.map((u) => u.id);
        }
      }

      await replyMutation.mutateAsync({
        ticketId: ticket.id,
        message: replyMessage.trim(),
        status: nextStatus,
        attachments: uploadedAttachmentIds,
      });

      // Cleanup object URLs
      adminAttachments.forEach((a) => {
        if (a.previewUrl) {
          try {
            URL.revokeObjectURL(a.previewUrl);
          } catch (err) {}
        }
      });

      setReplyMessage("");
      setAdminAttachments([]);
      toast.success("Reply submitted to user successfully.");
      refetch();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to submit admin reply.");
    } finally {
      setIsUploadingAttachments(false);
    }
  };

  // Handle Admin Internal Note
  const handleSubmitInternalNote = async (e) => {
    e.preventDefault();
    if (!internalNote.trim()) {
      toast.error("Internal note cannot be empty.");
      return;
    }

    try {
      await internalNoteMutation.mutateAsync({
        ticketId: ticket.id,
        note: internalNote.trim(),
      });
      setInternalNote("");
      toast.success("Confidential internal note saved.");
      refetch();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to save internal note.");
    }
  };

  // Handle Status Update
  const handleConfirmStatusUpdate = async () => {
    try {
      await statusMutation.mutateAsync({
        ticketId: ticket.id,
        status: targetStatus,
        note: statusReason.trim() || undefined,
      });
      setStatusChangeModalOpen(false);
      setStatusReason("");
      toast.success(`Ticket status updated to ${targetStatus}.`);
      refetch();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to update ticket status.");
    }
  };

  // Handle Assignment
  const handleAssignAdmin = async (newAdminId) => {
    try {
      await assignMutation.mutateAsync({
        ticketId: ticket.id,
        admin_id: newAdminId || null,
      });
      toast.success(newAdminId ? "Ticket assigned successfully." : "Ticket unassigned.");
      refetch();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to assign ticket.");
    }
  };

  // Handle Priority Change
  const handlePriorityChange = async (newPriority) => {
    try {
      await priorityMutation.mutateAsync({
        ticketId: ticket.id,
        priority: newPriority,
      });
      toast.success(`Priority set to ${newPriority}.`);
      refetch();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to update priority.");
    }
  };

  return (
    <div id="admin-ticket-workspace" className="space-y-4">
      {/* Workspace Header Card */}
      <EasyXCard className="p-4 sm:p-5 space-y-4 border-l-4 border-l-ex-primary">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-mono text-sm font-bold text-ex-lav-300">
                #{ticket.id.slice(-6).toUpperCase()}
              </span>
              <SupportStatusBadge status={ticket.status} />
              <SupportPriorityBadge priority={ticket.priority} />
              <SupportCategoryBadge category={ticket.category} />
            </div>
            <h2 className="text-base sm:text-lg font-bold text-white tracking-tight">
              {ticket.subject}
            </h2>
          </div>

          <div className="flex items-center gap-1.5 shrink-0">
            <button
              onClick={onClose}
              className="p-1.5 rounded-full hover:bg-white/10 text-white/50 hover:text-white transition"
              title="Close Detail View"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* User Identity Banner */}
        <div className="bg-white/[0.03] border border-white/8 rounded-ex-surface p-3.5 text-xs grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div>
            <span className="text-white/40 block text-[11px] font-medium">Customer Identity</span>
            <span className="font-semibold text-white truncate block mt-0.5">
              {user?.name || ticket.user_name || "Unknown"}
            </span>
            <span className="text-white/50 text-[11px] truncate block">
              {user?.email || ticket.user_email}
            </span>
          </div>

          <div>
            <span className="text-white/40 block text-[11px] font-medium">Account Status</span>
            <div className="flex items-center gap-2 mt-0.5">
              <span
                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold ${
                  user?.status === "active"
                    ? "bg-emerald-500/10 text-emerald-300 border border-emerald-500/20"
                    : "bg-rose-500/10 text-rose-300 border border-rose-500/20"
                }`}
              >
                {user?.status?.toUpperCase() || "ACTIVE"}
              </span>

              <span
                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold ${
                  user?.kyc_status === "approved"
                    ? "bg-emerald-500/10 text-emerald-300 border border-emerald-500/20"
                    : "bg-amber-500/10 text-amber-300 border border-amber-500/20"
                }`}
              >
                KYC: {user?.kyc_status?.toUpperCase() || "NONE"}
              </span>
            </div>
          </div>

          <div>
            <span className="text-white/40 block text-[11px] font-medium">Created / Last Activity</span>
            <span className="text-white/80 block mt-0.5">
              {dayjs(ticket.created_at).format("DD MMM YYYY, HH:mm")}
            </span>
            <span className="text-white/40 text-[11px] block">
              Active {dayjs(ticket.last_activity_at).fromNow()}
            </span>
          </div>
        </div>

        {/* Action Controls Bar (Assign, Status, Priority) */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-white/8 text-xs">
          <div className="flex items-center gap-2 flex-wrap">
            {/* Assign staff */}
            <div className="flex items-center gap-1.5">
              <UserCheck className="h-3.5 w-3.5 text-white/40" />
              <select
                id="select-ticket-assign-admin"
                value={ticket.assigned_admin_id || ""}
                onChange={(e) => handleAssignAdmin(e.target.value)}
                disabled={assignMutation.isPending}
                className="bg-white/5 border border-white/10 rounded-ex-ctrl px-2.5 py-1 text-xs text-white focus:outline-none focus:border-ex-primary"
              >
                <option value="" className="bg-[#12111c] text-white">Unassigned</option>
                {adminUsers.map((adm) => (
                  <option key={adm.id} value={adm.id} className="bg-[#12111c] text-white">
                    {adm.name || adm.email}
                  </option>
                ))}
              </select>
            </div>

            {/* Change Priority */}
            <div className="flex items-center gap-1.5">
              <select
                id="select-ticket-priority"
                value={ticket.priority}
                onChange={(e) => handlePriorityChange(e.target.value)}
                disabled={priorityMutation.isPending}
                className="bg-white/5 border border-white/10 rounded-ex-ctrl px-2.5 py-1 text-xs text-white focus:outline-none focus:border-ex-primary"
              >
                <option value="LOW" className="bg-[#12111c] text-white">Low Priority</option>
                <option value="NORMAL" className="bg-[#12111c] text-white">Normal Priority</option>
                <option value="HIGH" className="bg-[#12111c] text-white">High Priority</option>
                <option value="URGENT" className="bg-[#12111c] text-white">Urgent Priority</option>
              </select>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              id="btn-update-ticket-status"
              onClick={() => {
                setTargetStatus(ticket.status === "RESOLVED" ? "CLOSED" : "RESOLVED");
                setStatusChangeModalOpen(true);
              }}
              className="px-3 py-1 rounded-ex-ctrl bg-white/5 hover:bg-white/10 border border-white/10 text-white font-medium transition"
            >
              Update Status...
            </button>
          </div>
        </div>
      </EasyXCard>

      {/* Conversation Thread Messages */}
      <EasyXCard className="p-4 sm:p-5 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-white/8">
          <div className="flex items-center gap-2 text-xs font-semibold text-white/80">
            <MessageSquare className="h-4 w-4 text-ex-primary" />
            <span>Ticket Conversation History ({messages.length})</span>
          </div>
          <span className="text-[11px] text-white/40">Chronological Audit Log</span>
        </div>

        <div className="space-y-3 max-h-[460px] overflow-y-auto pr-1">
          {messages.map((msg) => {
            const isUser = msg.sender_type === "USER";
            const isAdmin = msg.sender_type === "ADMIN";
            const isInternalNote = msg.is_internal_note || msg.sender_type === "INTERNAL_NOTE";
            const isSystem = msg.sender_type === "SYSTEM";

            if (isSystem) {
              return (
                <div key={msg.id} className="text-center my-2">
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] bg-white/5 text-white/50 border border-white/5">
                    <Shield className="h-3 w-3 text-ex-lav-300" />
                    {msg.message} • {dayjs(msg.created_at).format("HH:mm")}
                  </span>
                </div>
              );
            }

            if (isInternalNote) {
              return (
                <div
                  key={msg.id}
                  id={`msg-internal-${msg.id}`}
                  className="rounded-ex-surface p-3.5 bg-amber-500/10 border border-amber-500/30 text-xs space-y-1.5"
                >
                  <div className="flex items-center justify-between text-[11px] text-amber-300 font-semibold">
                    <span className="inline-flex items-center gap-1">
                      <StickyNote className="h-3.5 w-3.5" />
                      CONFIDENTIAL ADMIN NOTE (Hidden from User)
                    </span>
                    <span className="text-amber-400/60 font-normal">
                      {msg.sender_name} • {dayjs(msg.created_at).format("DD MMM, HH:mm")}
                    </span>
                  </div>
                  <p className="text-amber-100 whitespace-pre-wrap leading-relaxed">{msg.message}</p>
                </div>
              );
            }

            return (
              <div
                key={msg.id}
                id={`msg-${msg.id}`}
                className={`rounded-ex-surface p-3.5 text-xs space-y-1.5 border transition ${
                  isUser
                    ? "bg-white/[0.04] border-white/10 text-white"
                    : "bg-ex-primary/10 border-ex-primary/30 text-white ml-4"
                }`}
              >
                <div className="flex items-center justify-between text-[11px]">
                  <div className="flex items-center gap-1.5">
                    <span
                      className={`font-semibold ${
                        isUser ? "text-ex-lav-300" : "text-emerald-400"
                      }`}
                    >
                      {msg.sender_name || (isUser ? "Customer" : "EasyX Support")}
                    </span>
                    <span
                      className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${
                        isUser ? "bg-white/10 text-white/70" : "bg-emerald-500/15 text-emerald-300"
                      }`}
                    >
                      {msg.sender_type}
                    </span>
                  </div>

                  <span className="text-white/40">{dayjs(msg.created_at).format("DD MMM, HH:mm")}</span>
                </div>

                <p className="text-white/90 whitespace-pre-wrap leading-relaxed">{msg.message}</p>

                {msg.attachments && msg.attachments.length > 0 && (
                  <SupportAttachmentViewer attachments={msg.attachments} />
                )}
              </div>
            );
          })}
          <div ref={messagesEndRef} />
        </div>
      </EasyXCard>

      {/* Admin Action Tabs & Composer (Reply vs Internal Note) */}
      <EasyXCard className="p-4 sm:p-5 space-y-4">
        <div className="flex items-center gap-2 border-b border-white/8 pb-3">
          <button
            id="tab-composer-reply"
            type="button"
            onClick={() => setActiveTab("REPLY")}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-ex-ctrl text-xs font-semibold transition ${
              activeTab === "REPLY"
                ? "bg-ex-primary text-white"
                : "text-white/60 hover:text-white hover:bg-white/5"
            }`}
          >
            <Send className="h-3.5 w-3.5" />
            Reply to User
          </button>

          <button
            id="tab-composer-note"
            type="button"
            onClick={() => setActiveTab("INTERNAL_NOTE")}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-ex-ctrl text-xs font-semibold transition ${
              activeTab === "INTERNAL_NOTE"
                ? "bg-amber-500 text-black font-bold"
                : "text-amber-400/80 hover:text-amber-300 hover:bg-amber-500/10"
            }`}
          >
            <StickyNote className="h-3.5 w-3.5" />
            Add Internal Staff Note (Confidential)
          </button>
        </div>

        {activeTab === "REPLY" ? (
          <form onSubmit={handleSubmitReply} className="space-y-3">
            <div>
              <textarea
                id="input-admin-reply"
                rows={4}
                value={replyMessage}
                onChange={(e) => setReplyMessage(e.target.value)}
                placeholder="Type your official support response to the user..."
                className="w-full bg-white/5 border border-white/10 rounded-ex-ctrl p-3 text-sm text-white placeholder:text-white/40 focus:outline-none focus:border-ex-primary transition resize-y"
                disabled={replyMutation.isPending || isUploadingAttachments}
              />
            </div>

            {/* Screenshots Uploader */}
            <SupportAttachmentUploader
              files={adminAttachments}
              onChange={setAdminAttachments}
              disabled={replyMutation.isPending || isUploadingAttachments}
              maxFiles={3}
              maxSizeMb={5}
              compact
            />

            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1">
              <div className="flex items-center gap-2">
                <span className="text-xs text-white/50">Status after reply:</span>
                <select
                  id="select-reply-status"
                  value={nextStatus}
                  onChange={(e) => setNextStatus(e.target.value)}
                  className="bg-white/5 border border-white/10 rounded-ex-ctrl px-2.5 py-1 text-xs text-white focus:outline-none focus:border-ex-primary"
                >
                  <option value="WAITING_FOR_USER" className="bg-[#12111c] text-white">Waiting for User</option>
                  <option value="IN_PROGRESS" className="bg-[#12111c] text-white">In Progress</option>
                  <option value="RESOLVED" className="bg-[#12111c] text-white">Mark as Resolved</option>
                  <option value="CLOSED" className="bg-[#12111c] text-white">Mark as Closed</option>
                </select>
              </div>

              <EasyXButton
                id="btn-submit-admin-reply"
                type="submit"
                loading={replyMutation.isPending || isUploadingAttachments}
                disabled={!replyMessage.trim() && adminAttachments.length === 0}
                className="w-full sm:w-auto"
              >
                Send Reply to Customer
              </EasyXButton>
            </div>
          </form>
        ) : (
          <form onSubmit={handleSubmitInternalNote} className="space-y-3">
            <div className="p-2.5 rounded-md bg-amber-500/10 border border-amber-500/20 text-[11px] text-amber-200">
              <ShieldAlert className="inline h-3.5 w-3.5 mr-1 align-text-bottom" />
              Internal notes are only visible to platform admins and will never be shown to the user.
            </div>

            <div>
              <textarea
                id="input-admin-internal-note"
                rows={3}
                value={internalNote}
                onChange={(e) => setInternalNote(e.target.value)}
                placeholder="Log internal diagnostics, supervisor instructions, or account review notes..."
                className="w-full bg-amber-500/[0.03] border border-amber-500/20 rounded-ex-ctrl p-3 text-sm text-amber-100 placeholder:text-amber-300/40 focus:outline-none focus:border-amber-400 transition resize-y"
              />
            </div>

            <div className="flex justify-end pt-1">
              <button
                id="btn-submit-internal-note"
                type="submit"
                disabled={internalNoteMutation.isPending || !internalNote.trim()}
                className="px-4 py-2 rounded-ex-ctrl bg-amber-500 hover:bg-amber-400 text-black font-bold text-xs transition disabled:opacity-50"
              >
                {internalNoteMutation.isPending ? "Saving Note..." : "Save Internal Note"}
              </button>
            </div>
          </form>
        )}
      </EasyXCard>

      {/* Status Change Modal */}
      <EasyXModal
        open={statusChangeModalOpen}
        onOpenChange={setStatusChangeModalOpen}
        title="Update Ticket Status"
        description="Change the lifecycle state of this customer support ticket."
      >
        <div className="space-y-4 text-xs pt-2">
          <div>
            <label className="block text-white/60 mb-1 font-medium">New Status</label>
            <select
              id="select-modal-status"
              value={targetStatus}
              onChange={(e) => setTargetStatus(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-ex-ctrl px-3 py-2 text-sm text-white focus:outline-none focus:border-ex-primary"
            >
              <option value="OPEN" className="bg-[#12111c] text-white">OPEN</option>
              <option value="IN_PROGRESS" className="bg-[#12111c] text-white">IN_PROGRESS</option>
              <option value="WAITING_FOR_USER" className="bg-[#12111c] text-white">WAITING_FOR_USER</option>
              <option value="WAITING_FOR_ADMIN" className="bg-[#12111c] text-white">WAITING_FOR_ADMIN</option>
              <option value="RESOLVED" className="bg-[#12111c] text-white">RESOLVED</option>
              <option value="CLOSED" className="bg-[#12111c] text-white">CLOSED</option>
            </select>
          </div>

          <div>
            <label className="block text-white/60 mb-1 font-medium">System / Audit Note (Optional)</label>
            <input
              id="input-modal-status-reason"
              type="text"
              placeholder="e.g. Issue resolved after verification check"
              value={statusReason}
              onChange={(e) => setStatusReason(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-ex-ctrl px-3 py-2 text-xs text-white placeholder:text-white/40 focus:outline-none focus:border-ex-primary"
            />
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-white/10">
            <EasyXButton variant="ghost" onClick={() => setStatusChangeModalOpen(false)}>
              Cancel
            </EasyXButton>
            <EasyXButton
              id="btn-confirm-status-update"
              onClick={handleConfirmStatusUpdate}
              loading={statusMutation.isPending}
            >
              Confirm Status
            </EasyXButton>
          </div>
        </div>
      </EasyXModal>
    </div>
  );
}
