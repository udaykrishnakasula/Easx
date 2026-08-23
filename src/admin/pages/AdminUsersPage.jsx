import React, { useMemo, useState } from "react";
import {
  Users,
  Search,
  Ban,
  CheckCircle2,
  ShieldAlert,
  Wallet as WalletIcon,
  PiggyBank,
  Share2,
  BadgeCheck,
  Eye,
  Calendar,
  Phone,
  Mail,
  AlertTriangle,
  Lock,
} from "lucide-react";
import { toast } from "sonner";

import { useAdminUsers, useSuspendUser, useUnsuspendUser } from "@/admin/adminApi";
import { apiError } from "@/shared/lib/api";
import {
  PageHeading,
  EasyXCard,
  EasyXButton,
  EasyXLoader,
  EasyXTable,
  EasyXBadge,
  EasyXEmptyState,
  EasyXModal,
} from "@/design/EasyX";

const STATUS_FILTERS = [
  { key: "", label: "All Users" },
  { key: "active", label: "Active" },
  { key: "suspended", label: "Suspended" },
];

function StatusPill({ status }) {
  if (status === "suspended" || status === "banned") {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20">
        <Ban className="h-3 w-3" />
        SUSPENDED
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
      <CheckCircle2 className="h-3 w-3" />
      ACTIVE
    </span>
  );
}

function KycPill({ status }) {
  const map = {
    approved: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
    pending: "bg-amber-500/10 text-amber-400 border border-amber-500/20",
    rejected: "bg-rose-500/10 text-rose-400 border border-rose-500/20",
    none: "bg-white/5 text-ex-muted border border-white/10",
  };
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
        map[status] || map.none
      }`}
    >
      <BadgeCheck className="h-3 w-3" />
      {status || "NONE"}
    </span>
  );
}

function money(v) {
  const n = Number(v);
  if (Number.isNaN(n)) return v ?? "0.00";
  return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function AdminUsersPage() {
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [q, setQ] = useState("");
  const { data, isLoading } = useAdminUsers({ status, q });
  const suspend = useSuspendUser();
  const unsuspend = useUnsuspendUser();

  const [suspendTarget, setSuspendTarget] = useState(null);
  const [suspendReason, setSuspendReason] = useState("");
  const [detailUser, setDetailUser] = useState(null);

  const users = data?.users || [];
  const total = data?.total ?? 0;

  const onSearch = (e) => {
    e.preventDefault();
    setQ(search.trim());
  };

  const doSuspend = async () => {
    if (suspendReason.trim().length < 3) {
      toast.error("Please provide a valid suspension reason (min 3 chars).");
      return;
    }
    try {
      await suspend.mutateAsync({ id: suspendTarget.id, reason: suspendReason.trim() });
      toast.success(`${suspendTarget.name || suspendTarget.email} has been suspended.`);
      setSuspendTarget(null);
      setSuspendReason("");
    } catch (err) {
      toast.error(apiError(err, "Could not suspend user"));
    }
  };

  const doUnsuspend = async (u) => {
    try {
      await unsuspend.mutateAsync({ id: u.id });
      toast.success(`${u.name || u.email} has been reactivated.`);
      if (detailUser?.id === u.id) {
        setDetailUser((prev) => (prev ? { ...prev, status: "active" } : null));
      }
    } catch (err) {
      toast.error(apiError(err, "Could not reactivate user"));
    }
  };

  const columns = useMemo(
    () => [
      "User / Referral Code",
      "Contact",
      "Account Status",
      "KYC",
      "Wallet (USDT)",
      "Investments",
      "Referrals",
      "Actions",
    ],
    []
  );

  return (
    <div className="space-y-6" data-testid="admin-users-page">
      <PageHeading
        title="Users Management"
        subtitle={`${total} registered member${total === 1 ? "" : "s"} — search, monitor portfolios, review KYC, and manage account access.`}
        icon={Users}
      />

      {/* Filter and Search Bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap gap-2" data-testid="users-status-filters">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f.key || "all"}
              onClick={() => setStatus(f.key)}
              className={`rounded-full px-4 py-1.5 text-xs font-semibold transition ${
                status === f.key
                  ? "bg-ex-accent text-ex-ink shadow-sm"
                  : "bg-white/5 text-ex-muted hover:bg-white/10 hover:text-ex-text"
              }`}
              data-testid={`users-filter-${f.key || "all"}`}
            >
              {f.label}
            </button>
          ))}
        </div>

        <form onSubmit={onSearch} className="relative w-full sm:w-80">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ex-muted" />
          <input
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              if (e.target.value === "") setQ("");
            }}
            placeholder="Search name, email, phone, code..."
            className="w-full rounded-ex-ctrl bg-white/5 border border-white/10 pl-9 pr-3 py-2 text-sm text-ex-text placeholder:text-ex-muted/60 focus:border-ex-accent focus:outline-none"
            data-testid="users-search-input"
          />
        </form>
      </div>

      {/* Main Table / Loader */}
      {isLoading ? (
        <EasyXLoader />
      ) : users.length === 0 ? (
        <EasyXEmptyState
          icon={Users}
          title="No users found"
          description="No user accounts match the selected status filter or search term."
        />
      ) : (
        <EasyXCard className="p-0 overflow-hidden border border-white/8">
          <div className="overflow-x-auto">
            <EasyXTable columns={columns}>
              {users.map((u) => (
                <tr
                  key={u.id}
                  data-testid={`user-row-${u.id}`}
                  className="hover:bg-white/[0.02] transition divide-y divide-white/4"
                >
                  {/* User name & code */}
                  <td className="px-4 py-3.5">
                    <div className="font-semibold text-ex-text">{u.name || "—"}</div>
                    <div className="text-xs text-ex-lav-300 font-mono mt-0.5">
                      Code: {u.referral_code || "—"}
                    </div>
                  </td>

                  {/* Contact */}
                  <td className="px-4 py-3.5">
                    <div className="text-sm text-ex-text flex items-center gap-1.5">
                      <Mail className="h-3.5 w-3.5 text-ex-muted shrink-0" />
                      <span className="truncate">{u.email}</span>
                    </div>
                    <div className="text-xs text-ex-muted flex items-center gap-1.5 mt-0.5">
                      <Phone className="h-3 w-3 shrink-0" />
                      <span>{u.phone || "—"}</span>
                    </div>
                  </td>

                  {/* Status */}
                  <td className="px-4 py-3.5">
                    <StatusPill status={u.status} />
                  </td>

                  {/* KYC */}
                  <td className="px-4 py-3.5">
                    <KycPill status={u.kyc_status} />
                  </td>

                  {/* Wallet Summary */}
                  <td className="px-4 py-3.5">
                    <div className="font-semibold text-ex-text">
                      {money(u.wallet?.available_balance)} USDT
                    </div>
                    <div className="text-[11px] text-ex-muted">
                      Locked: {money(u.wallet?.locked_investment)}
                    </div>
                  </td>

                  {/* Investment Summary */}
                  <td className="px-4 py-3.5">
                    <div className="text-sm font-semibold text-ex-text">
                      {u.investments?.active || 0} active
                    </div>
                    <div className="text-[11px] text-ex-muted">
                      {money(u.investments?.active_principal)} USDT
                    </div>
                  </td>

                  {/* Referral Summary */}
                  <td className="px-4 py-3.5">
                    <div className="text-sm font-semibold text-ex-text">
                      {u.referrals?.total_referred || 0} invited
                    </div>
                    <div className="text-[11px] text-ex-muted">
                      Earned: {money(u.referrals?.commission_earned)} USDT
                    </div>
                  </td>

                  {/* Action Buttons */}
                  <td className="px-4 py-3.5 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => setDetailUser(u)}
                        className="px-2.5 py-1.5 rounded-ex-ctrl text-xs font-semibold bg-white/5 hover:bg-white/10 text-ex-lav-200 hover:text-white transition flex items-center gap-1"
                        title="View Full Profile & Portfolios"
                      >
                        <Eye className="h-3.5 w-3.5" />
                        <span>View</span>
                      </button>

                      {u.status === "suspended" ? (
                        <button
                          onClick={() => doUnsuspend(u)}
                          disabled={unsuspend.isPending}
                          className="px-2.5 py-1.5 rounded-ex-ctrl text-xs font-semibold bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 transition flex items-center gap-1"
                        >
                          <CheckCircle2 className="h-3.5 w-3.5" />
                          <span>Unsuspend</span>
                        </button>
                      ) : (
                        <button
                          onClick={() => {
                            setSuspendTarget(u);
                            setSuspendReason("");
                          }}
                          className="px-2.5 py-1.5 rounded-ex-ctrl text-xs font-semibold bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 transition flex items-center gap-1"
                        >
                          <Ban className="h-3.5 w-3.5" />
                          <span>Suspend</span>
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </EasyXTable>
          </div>
        </EasyXCard>
      )}

      {/* USER DETAIL MODAL */}
      <EasyXModal
        open={Boolean(detailUser)}
        onClose={() => setDetailUser(null)}
        title="User Profile & Portfolio Overview"
      >
        {detailUser && (
          <div className="space-y-5 text-sm">
            {/* Header info */}
            <div className="flex items-start justify-between gap-4 p-4 rounded-ex-card bg-white/[0.03] border border-white/8">
              <div>
                <div className="text-base font-bold text-ex-text">{detailUser.name}</div>
                <div className="text-xs text-ex-muted mt-0.5">{detailUser.email}</div>
                <div className="text-xs text-ex-muted">{detailUser.phone}</div>
              </div>
              <div className="flex flex-col items-end gap-1.5">
                <StatusPill status={detailUser.status} />
                <KycPill status={detailUser.kyc_status} />
              </div>
            </div>

            {/* Account Metrics Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <div className="p-3 rounded-ex-card bg-white/[0.02] border border-white/6">
                <div className="text-xs text-ex-muted">Available Balance</div>
                <div className="text-base font-bold text-ex-text mt-1">
                  {money(detailUser.wallet?.available_balance)} USDT
                </div>
              </div>
              <div className="p-3 rounded-ex-card bg-white/[0.02] border border-white/6">
                <div className="text-xs text-ex-muted">Active Locked Principal</div>
                <div className="text-base font-bold text-ex-text mt-1">
                  {money(detailUser.wallet?.locked_investment)} USDT
                </div>
              </div>
              <div className="p-3 rounded-ex-card bg-white/[0.02] border border-white/6">
                <div className="text-xs text-ex-muted">Total Earned</div>
                <div className="text-base font-bold text-emerald-400 mt-1">
                  {money(detailUser.wallet?.total_earned)} USDT
                </div>
              </div>

              <div className="p-3 rounded-ex-card bg-white/[0.02] border border-white/6">
                <div className="text-xs text-ex-muted">Active Investments</div>
                <div className="text-base font-bold text-ex-text mt-1">
                  {detailUser.investments?.active || 0} plans
                </div>
              </div>
              <div className="p-3 rounded-ex-card bg-white/[0.02] border border-white/6">
                <div className="text-xs text-ex-muted">Matured Investments</div>
                <div className="text-base font-bold text-ex-text mt-1">
                  {detailUser.investments?.matured || 0} plans
                </div>
              </div>
              <div className="p-3 rounded-ex-card bg-white/[0.02] border border-white/6">
                <div className="text-xs text-ex-muted">Affiliate Direct Referrals</div>
                <div className="text-base font-bold text-ex-text mt-1">
                  {detailUser.referrals?.total_referred || 0} members
                </div>
              </div>
            </div>

            {/* Suspension state banner if applicable */}
            {detailUser.status === "suspended" && (
              <div className="p-3.5 rounded-ex-card bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2.5">
                <AlertTriangle className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
                <div>
                  <div className="font-bold">Account is currently suspended</div>
                  <div className="mt-0.5 text-rose-300/80">
                    Reason: {detailUser.suspended_reason || "Administrative policy enforcement"}
                  </div>
                  <div className="mt-1 text-[11px] text-ex-muted">
                    Note: Existing active investments remain in effect and continue toward maturity.
                  </div>
                </div>
              </div>
            )}

            {/* Modal actions */}
            <div className="flex items-center justify-end gap-3 pt-2 border-t border-white/8">
              {detailUser.status === "suspended" ? (
                <EasyXButton
                  onClick={() => doUnsuspend(detailUser)}
                  loading={unsuspend.isPending}
                  className="bg-emerald-500 hover:bg-emerald-600 text-white font-semibold"
                >
                  <CheckCircle2 className="h-4 w-4 mr-1.5" /> Reactivate Account
                </EasyXButton>
              ) : (
                <EasyXButton
                  onClick={() => {
                    const u = detailUser;
                    setDetailUser(null);
                    setSuspendTarget(u);
                    setSuspendReason("");
                  }}
                  className="bg-rose-500 hover:bg-rose-600 text-white font-semibold"
                >
                  <Ban className="h-4 w-4 mr-1.5" /> Suspend Account
                </EasyXButton>
              )}
            </div>
          </div>
        )}
      </EasyXModal>

      {/* SUSPENSION CONFIRMATION MODAL */}
      <EasyXModal
        open={Boolean(suspendTarget)}
        onClose={() => setSuspendTarget(null)}
        title="Confirm Account Suspension"
      >
        {suspendTarget && (
          <div className="space-y-4 text-sm">
            <div className="p-3.5 rounded-ex-card bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs">
              <div className="font-bold flex items-center gap-1.5">
                <ShieldAlert className="h-4 w-4" />
                Important Suspension Policy
              </div>
              <div className="mt-1 leading-relaxed text-amber-200/90">
                Suspending <strong>{suspendTarget.name || suspendTarget.email}</strong> will prevent login,
                new investments, and withdrawals.
                <br />
                <span className="font-semibold text-white mt-1 block">
                  Existing active investments will NOT be cancelled and will continue toward scheduled maturity.
                </span>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-ex-muted mb-1.5">
                Reason for Suspension (recorded in Audit Log)
              </label>
              <textarea
                value={suspendReason}
                onChange={(e) => setSuspendReason(e.target.value)}
                placeholder="e.g. Terms of service violation, duplicate identity review, requested by user"
                rows={3}
                className="w-full rounded-ex-ctrl bg-white/5 border border-white/10 p-3 text-sm text-ex-text placeholder:text-ex-muted/50 focus:border-rose-400 focus:outline-none"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-white/8">
              <button
                onClick={() => setSuspendTarget(null)}
                className="px-4 py-2 rounded-ex-ctrl text-sm text-ex-muted hover:text-ex-text hover:bg-white/5"
              >
                Cancel
              </button>
              <EasyXButton
                onClick={doSuspend}
                loading={suspend.isPending}
                className="bg-rose-500 hover:bg-rose-600 text-white font-semibold"
              >
                <Ban className="h-4 w-4 mr-1.5" /> Confirm Suspension
              </EasyXButton>
            </div>
          </div>
        )}
      </EasyXModal>
    </div>
  );
}
