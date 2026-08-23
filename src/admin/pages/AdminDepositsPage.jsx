import React, { useState } from "react";
import {
  Inbox,
  Check,
  X,
  Eye,
  Calendar,
  Layers,
  ArrowUpRight,
  Copy,
  CheckCheck,
  ShieldCheck,
  AlertCircle,
  Hash,
} from "lucide-react";
import { toast } from "sonner";
import dayjs from "dayjs";

import {
  useAdminDeposits,
  useApproveDeposit,
  useRejectDeposit,
} from "@/admin/adminApi";
import { money } from "@/user/api";
import { apiError } from "@/shared/lib/api";
import {
  PageHeading,
  EasyXCard,
  EasyXButton,
  EasyXLoader,
  EasyXEmptyState,
  EasyXModal,
} from "@/design/EasyX";

const FILTERS = [
  { key: "pending", label: "Pending Review" },
  { key: "approved", label: "Approved" },
  { key: "rejected", label: "Rejected" },
  { key: "", label: "All Deposits" },
];

function StatusBadge({ status }) {
  if (status === "approved") {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
        <Check className="h-3 w-3" /> APPROVED
      </span>
    );
  }
  if (status === "rejected") {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20">
        <X className="h-3 w-3" /> REJECTED
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">
      PENDING
    </span>
  );
}

function NetworkBadge({ network }) {
  const isTrc = network === "TRC20";
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-bold ${
        isTrc
          ? "bg-rose-500/15 text-rose-300 border border-rose-500/30"
          : "bg-amber-500/15 text-amber-300 border border-amber-500/30"
      }`}
    >
      {network}
    </span>
  );
}

export default function AdminDepositsPage() {
  const [filter, setFilter] = useState("pending");
  const { data: deposits, isLoading } = useAdminDeposits(filter);
  const approve = useApproveDeposit();
  const reject = useRejectDeposit();

  const [modal, setModal] = useState(null); // { type: 'approve'|'reject'|'view', deposit }
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [copiedHash, setCopiedHash] = useState(false);

  const openApprove = (d) => {
    setModal({ type: "approve", deposit: d });
    setAmount(String(d.amount));
    setNote("");
  };

  const openReject = (d) => {
    setModal({ type: "reject", deposit: d });
    setNote("");
  };

  const openView = (d) => {
    setModal({ type: "view", deposit: d });
    setCopiedHash(false);
  };

  const close = () => setModal(null);

  const doApprove = async () => {
    if (!amount || Number(amount) <= 0) {
      toast.error("Please enter a valid deposit amount.");
      return;
    }
    try {
      await approve.mutateAsync({ id: modal.deposit.id, approved_amount: amount, note });
      toast.success(`Deposit approved: ${money(amount)} USDT credited to user wallet`);
      close();
    } catch (e) {
      toast.error(apiError(e, "Could not approve deposit"));
    }
  };

  const doReject = async () => {
    try {
      await reject.mutateAsync({ id: modal.deposit.id, note });
      toast.success("Deposit rejected. No wallet funds credited.");
      close();
    } catch (e) {
      toast.error(apiError(e, "Could not reject deposit"));
    }
  };

  const copyTxHash = (hash) => {
    if (!hash) return;
    navigator.clipboard.writeText(hash);
    setCopiedHash(true);
    toast.success("Transaction hash copied to clipboard");
    setTimeout(() => setCopiedHash(false), 2000);
  };

  return (
    <div className="space-y-6" data-testid="admin-deposits-page">
      <PageHeading
        title="Deposit Verification"
        subtitle="Review, approve, and verify incoming USDT blockchain deposits (TRC20 & BEP20)."
        icon={Inbox}
      />

      {/* Filter Bar */}
      <div className="flex flex-wrap gap-2" data-testid="admin-deposit-filters">
        {FILTERS.map((f) => (
          <button
            key={f.key || "all"}
            onClick={() => setFilter(f.key)}
            data-testid={`admin-filter-${f.key || "all"}`}
            className={`px-4 py-1.5 rounded-full text-xs font-semibold transition ${
              filter === f.key
                ? "bg-ex-accent text-ex-ink shadow-sm"
                : "bg-white/5 text-ex-muted hover:bg-white/10 hover:text-ex-text"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Main List */}
      <div>
        {isLoading ? (
          <EasyXLoader />
        ) : !deposits || deposits.length === 0 ? (
          <EasyXEmptyState
            icon={Inbox}
            title="No deposits found"
            description="No transactions match the selected filter."
          />
        ) : (
          <div className="space-y-3">
            {deposits.map((d) => (
              <EasyXCard
                key={d.id}
                className="p-5 border border-white/8 hover:border-white/16 transition-all"
                data-testid={`admin-deposit-${d.id}`}
              >
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                  {/* Left Column: Details */}
                  <div className="space-y-2 min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2.5">
                      <span className="text-xl font-extrabold text-ex-text">
                        {money(d.amount)} USDT
                      </span>
                      <NetworkBadge network={d.network} />
                      <StatusBadge status={d.status} />
                      {d.status === "approved" && d.approved_amount && (
                        <span className="text-xs font-semibold text-emerald-400">
                          (Credited: {money(d.approved_amount)} USDT)
                        </span>
                      )}
                    </div>

                    {/* Metadata Grid */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-2 text-xs text-ex-muted">
                      <div>
                        <span className="text-ex-muted/60">User:</span>{" "}
                        <strong className="text-ex-text font-medium">
                          {d.user?.name || "—"}
                        </strong>{" "}
                        <span className="text-[11px] block truncate">{d.user?.email || d.user_id}</span>
                      </div>

                      <div>
                        <span className="text-ex-muted/60">Deposit ID:</span>{" "}
                        <span className="font-mono text-[11px] text-ex-lav-200 block truncate">
                          {d.id}
                        </span>
                      </div>

                      <div className="min-w-0">
                        <span className="text-ex-muted/60">Tx Hash:</span>
                        <div className="font-mono text-[11px] text-ex-text truncate flex items-center gap-1">
                          <span className="truncate">{d.tx_hash}</span>
                        </div>
                      </div>

                      <div>
                        <span className="text-ex-muted/60">Submitted Date:</span>
                        <div className="text-ex-text font-medium">
                          {dayjs(d.created_at).format("DD MMM YYYY, HH:mm")}
                        </div>
                      </div>
                    </div>

                    {d.admin_note && (
                      <div className="text-xs p-2 rounded-md bg-white/[0.03] border border-white/6 text-ex-muted">
                        <span className="font-semibold text-ex-text">Admin Note:</span> {d.admin_note}
                      </div>
                    )}
                  </div>

                  {/* Right Column: Actions */}
                  <div className="flex items-center gap-2 shrink-0 self-end lg:self-center">
                    <button
                      onClick={() => openView(d)}
                      className="px-3 py-2 rounded-ex-ctrl text-xs font-semibold bg-white/5 hover:bg-white/10 text-ex-text transition flex items-center gap-1.5"
                    >
                      <Eye className="h-3.5 w-3.5" /> View Details
                    </button>

                    {d.status === "pending" && (
                      <>
                        <EasyXButton
                          variant="accent"
                          className="h-9 px-3.5 text-xs font-bold"
                          onClick={() => openApprove(d)}
                          data-testid={`admin-approve-${d.id}`}
                        >
                          <Check className="mr-1 h-3.5 w-3.5" /> Approve
                        </EasyXButton>
                        <EasyXButton
                          variant="ghost"
                          className="h-9 px-3.5 text-xs font-bold text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 border border-rose-500/20"
                          onClick={() => openReject(d)}
                          data-testid={`admin-reject-${d.id}`}
                        >
                          <X className="mr-1 h-3.5 w-3.5" /> Reject
                        </EasyXButton>
                      </>
                    )}
                  </div>
                </div>
              </EasyXCard>
            ))}
          </div>
        )}
      </div>

      {/* DETAIL MODAL */}
      <EasyXModal
        open={modal?.type === "view"}
        onClose={close}
        title="Deposit Transaction Inspection"
      >
        {modal?.deposit && (
          <div className="space-y-4 text-sm">
            <div className="flex items-center justify-between p-3.5 rounded-ex-card bg-white/[0.03] border border-white/8">
              <div>
                <div className="text-xs text-ex-muted">Submitted Amount</div>
                <div className="text-xl font-extrabold text-ex-text mt-0.5">
                  {money(modal.deposit.amount)} USDT
                </div>
              </div>
              <div className="flex flex-col items-end gap-1.5">
                <NetworkBadge network={modal.deposit.network} />
                <StatusBadge status={modal.deposit.status} />
              </div>
            </div>

            <div className="space-y-2.5 text-xs">
              <div className="p-2.5 rounded-ex-ctrl bg-white/[0.02] border border-white/6 flex justify-between">
                <span className="text-ex-muted">User</span>
                <span className="font-semibold text-ex-text">
                  {modal.deposit.user?.name || "—"} ({modal.deposit.user?.email || modal.deposit.user_id})
                </span>
              </div>

              <div className="p-2.5 rounded-ex-ctrl bg-white/[0.02] border border-white/6 flex justify-between items-center">
                <span className="text-ex-muted">Deposit ID</span>
                <span className="font-mono text-ex-lav-200">{modal.deposit.id}</span>
              </div>

              <div className="p-2.5 rounded-ex-ctrl bg-white/[0.02] border border-white/6">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-ex-muted">Transaction Hash</span>
                  <button
                    onClick={() => copyTxHash(modal.deposit.tx_hash)}
                    className="text-ex-accent hover:underline flex items-center gap-1 font-semibold"
                  >
                    {copiedHash ? <CheckCheck className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                    {copiedHash ? "Copied" : "Copy"}
                  </button>
                </div>
                <div className="font-mono text-ex-text break-all bg-black/40 p-2 rounded border border-white/6">
                  {modal.deposit.tx_hash}
                </div>
              </div>

              <div className="p-2.5 rounded-ex-ctrl bg-white/[0.02] border border-white/6 flex justify-between">
                <span className="text-ex-muted">Submitted Date</span>
                <span className="text-ex-text">
                  {dayjs(modal.deposit.created_at).format("DD MMM YYYY, HH:mm:ss")}
                </span>
              </div>

              {modal.deposit.decided_at && (
                <div className="p-2.5 rounded-ex-ctrl bg-white/[0.02] border border-white/6 flex justify-between">
                  <span className="text-ex-muted">Decision Date</span>
                  <span className="text-ex-text">
                    {dayjs(modal.deposit.decided_at).format("DD MMM YYYY, HH:mm:ss")}
                  </span>
                </div>
              )}
            </div>

            {modal.deposit.status === "pending" && (
              <div className="flex gap-2 pt-3 border-t border-white/8">
                <EasyXButton
                  variant="ghost"
                  className="flex-1 text-rose-400 hover:bg-rose-500/10 border border-rose-500/20"
                  onClick={() => openReject(modal.deposit)}
                >
                  <X className="mr-1.5 h-4 w-4" /> Reject
                </EasyXButton>
                <EasyXButton
                  variant="accent"
                  className="flex-1 font-bold"
                  onClick={() => openApprove(modal.deposit)}
                >
                  <Check className="mr-1.5 h-4 w-4" /> Approve Deposit
                </EasyXButton>
              </div>
            )}
          </div>
        )}
      </EasyXModal>

      {/* APPROVE MODAL */}
      <EasyXModal
        open={modal?.type === "approve"}
        onClose={close}
        title="Approve & Credit Deposit"
      >
        {modal?.deposit && (
          <div className="space-y-4 text-sm">
            <div className="p-3.5 rounded-ex-card bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs">
              <div className="font-bold flex items-center gap-1.5">
                <ShieldCheck className="h-4 w-4" />
                Wallet Ledger Transaction
              </div>
              <div className="mt-1 text-emerald-200/90 leading-relaxed">
                Approving will create an immutable credit ledger entry of exactly{" "}
                <strong>{money(amount || 0)} USDT</strong> to the user's available wallet balance.
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-ex-muted mb-1.5">
                Amount to Credit (USDT)
              </label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className="w-full rounded-ex-ctrl bg-white/5 border border-white/10 p-2.5 text-sm text-ex-text focus:border-ex-accent focus:outline-none"
                data-testid="admin-approve-amount"
              />
              <p className="mt-1 text-[11px] text-ex-muted">
                Submitted user amount: {money(modal.deposit.amount)} USDT.
              </p>
            </div>

            <div>
              <label className="block text-xs font-semibold text-ex-muted mb-1.5">
                Admin Note (Optional)
              </label>
              <input
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="e.g. Verified on Tronscan / BscScan"
                className="w-full rounded-ex-ctrl bg-white/5 border border-white/10 p-2.5 text-sm text-ex-text focus:border-ex-accent focus:outline-none"
              />
            </div>

            <div className="flex gap-2 pt-3 border-t border-white/8">
              <button
                onClick={close}
                className="flex-1 px-4 py-2 rounded-ex-ctrl text-sm text-ex-muted hover:text-ex-text hover:bg-white/5"
              >
                Cancel
              </button>
              <EasyXButton
                variant="accent"
                className="flex-1 font-bold"
                onClick={doApprove}
                loading={approve.isPending}
                data-testid="admin-approve-confirm"
              >
                <Check className="mr-1.5 h-4 w-4" /> Confirm & Credit
              </EasyXButton>
            </div>
          </div>
        )}
      </EasyXModal>

      {/* REJECT MODAL */}
      <EasyXModal
        open={modal?.type === "reject"}
        onClose={close}
        title="Reject Deposit"
      >
        {modal?.deposit && (
          <div className="space-y-4 text-sm">
            <div className="p-3.5 rounded-ex-card bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
              <div className="font-bold flex items-center gap-1.5">
                <AlertCircle className="h-4 w-4" />
                No Wallet Funds Will Be Credited
              </div>
              <div className="mt-1 text-rose-200/90 leading-relaxed">
                Rejecting deposit <strong>{modal.deposit.id}</strong> will mark it as rejected.
                An audit log and in-app user notification will be created.
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-ex-muted mb-1.5">
                Rejection Reason
              </label>
              <input
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="e.g. Invalid TX hash, incorrect address, or unconfirmed funds"
                className="w-full rounded-ex-ctrl bg-white/5 border border-white/10 p-2.5 text-sm text-ex-text focus:border-rose-400 focus:outline-none"
              />
            </div>

            <div className="flex gap-2 pt-3 border-t border-white/8">
              <button
                onClick={close}
                className="flex-1 px-4 py-2 rounded-ex-ctrl text-sm text-ex-muted hover:text-ex-text hover:bg-white/5"
              >
                Cancel
              </button>
              <EasyXButton
                onClick={doReject}
                loading={reject.isPending}
                className="flex-1 bg-rose-500 hover:bg-rose-600 text-white font-bold"
                data-testid="admin-reject-confirm"
              >
                <X className="mr-1.5 h-4 w-4" /> Confirm Rejection
              </EasyXButton>
            </div>
          </div>
        )}
      </EasyXModal>
    </div>
  );
}
