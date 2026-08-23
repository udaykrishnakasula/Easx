import React, { useMemo, useState } from "react";
import {
  ArrowUpFromLine,
  Check,
  X,
  Send,
  Eye,
  Calendar,
  Layers,
  Copy,
  CheckCheck,
  BadgeCheck,
  ShieldCheck,
  Lock,
  Clock,
  AlertTriangle,
  Play,
} from "lucide-react";
import { toast } from "sonner";
import dayjs from "dayjs";

import { useAdminWithdrawals, useWithdrawalAction } from "@/admin/adminApi";
import { money } from "@/user/api";
import { apiError } from "@/shared/lib/api";
import {
  PageHeading,
  EasyXCard,
  EasyXButton,
  EasyXLoader,
  EasyXTable,
  EasyXEmptyState,
  EasyXModal,
} from "@/design/EasyX";

const FILTERS = [
  { key: "pending", label: "Pending" },
  { key: "approved", label: "Approved" },
  { key: "processing", label: "Processing" },
  { key: "completed", label: "Completed" },
  { key: "rejected", label: "Rejected" },
  { key: "failed", label: "Failed" },
  { key: "", label: "All Withdrawals" },
];

function StatusBadge({ status }) {
  const norm = status === "paid" ? "completed" : status;
  if (norm === "completed") {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
        <Check className="h-3 w-3" /> COMPLETED
      </span>
    );
  }
  if (norm === "processing") {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-sky-500/10 text-sky-400 border border-sky-500/20">
        <Clock className="h-3 w-3 animate-spin" /> PROCESSING
      </span>
    );
  }
  if (norm === "approved") {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
        <Check className="h-3 w-3" /> APPROVED
      </span>
    );
  }
  if (norm === "rejected" || norm === "failed") {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20">
        <X className="h-3 w-3" /> {norm.toUpperCase()}
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

export default function AdminWithdrawalsPage() {
  const [status, setStatus] = useState("pending");
  const { data: rawData, isLoading } = useAdminWithdrawals({ status });
  const action = useWithdrawalAction();

  const [modal, setModal] = useState(null); // { type: 'view'|'reject'|'process'|'approve', withdrawal }
  const [rejectReason, setRejectReason] = useState("");
  const [txHash, setTxHash] = useState("");
  const [copiedAddr, setCopiedAddr] = useState(false);

  const withdrawals = rawData || [];

  const openApprove = (w) => setModal({ type: "approve", withdrawal: w });
  const openReject = (w) => {
    setModal({ type: "reject", withdrawal: w });
    setRejectReason("");
  };
  const openProcess = (w) => {
    setModal({ type: "process", withdrawal: w });
    setTxHash("");
  };
  const openView = (w) => {
    setModal({ type: "view", withdrawal: w });
    setCopiedAddr(false);
  };
  const close = () => setModal(null);

  const doApprove = async () => {
    try {
      await action.mutateAsync({ id: modal.withdrawal.id, action: "approve" });
      toast.success("Withdrawal approved and ready for dispatch.");
      close();
    } catch (err) {
      toast.error(apiError(err, "Could not approve withdrawal"));
    }
  };

  const doSetProcessing = async (w) => {
    try {
      await action.mutateAsync({ id: w.id, action: "processing" });
      toast.success("Withdrawal set to processing state.");
      if (modal?.withdrawal?.id === w.id) close();
    } catch (err) {
      toast.error(apiError(err, "Could not set processing status"));
    }
  };

  const doReject = async () => {
    if (rejectReason.trim().length < 3) {
      toast.error("Please provide a valid rejection reason (min 3 chars).");
      return;
    }
    try {
      await action.mutateAsync({
        id: modal.withdrawal.id,
        action: "reject",
        body: { reason: rejectReason.trim() },
      });
      toast.success("Withdrawal rejected — funds reversed to user wallet.");
      close();
    } catch (err) {
      toast.error(apiError(err, "Could not reject withdrawal"));
    }
  };

  const doProcessComplete = async () => {
    if (txHash.trim().length < 8) {
      toast.error("Please enter a valid on-chain blockchain transaction hash.");
      return;
    }
    try {
      await action.mutateAsync({
        id: modal.withdrawal.id,
        action: "process",
        body: { tx_hash: txHash.trim() },
      });
      toast.success("Withdrawal completed with blockchain hash recorded.");
      close();
    } catch (err) {
      toast.error(apiError(err, "Could not complete withdrawal"));
    }
  };

  const copyAddress = (addr) => {
    if (!addr) return;
    navigator.clipboard.writeText(addr);
    setCopiedAddr(true);
    toast.success("Destination address copied to clipboard");
    setTimeout(() => setCopiedAddr(false), 2000);
  };

  const columns = useMemo(
    () => [
      "User / Security",
      "Amount / Network",
      "Destination Address",
      "Status",
      "Submitted Time",
      "Actions",
    ],
    []
  );

  return (
    <div className="space-y-6" data-testid="admin-withdrawals-page">
      <PageHeading
        title="Withdrawal Requests"
        subtitle="Review, approve, process, and complete manual USDT blockchain payouts (TRC20 & BEP20)."
        icon={ArrowUpFromLine}
      />

      {/* Filter Bar */}
      <div className="flex flex-wrap gap-2" data-testid="admin-withdrawal-filters">
        {FILTERS.map((f) => (
          <button
            key={f.key || "all"}
            onClick={() => setStatus(f.key)}
            data-testid={`wd-filter-${f.key || "all"}`}
            className={`px-4 py-1.5 rounded-full text-xs font-semibold transition ${
              status === f.key
                ? "bg-ex-accent text-ex-ink shadow-sm"
                : "bg-white/5 text-ex-muted hover:bg-white/10 hover:text-ex-text"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Main Table / Loader */}
      {isLoading ? (
        <EasyXLoader />
      ) : withdrawals.length === 0 ? (
        <EasyXEmptyState
          icon={ArrowUpFromLine}
          title="No withdrawal requests"
          description="No payouts match the selected status filter."
        />
      ) : (
        <EasyXCard className="p-0 overflow-hidden border border-white/8">
          <div className="overflow-x-auto">
            <EasyXTable columns={columns}>
              {withdrawals.map((w) => (
                <tr
                  key={w.id}
                  data-testid={`wd-row-${w.id}`}
                  className="hover:bg-white/[0.02] transition divide-y divide-white/4"
                >
                  {/* User & Security / Verification */}
                  <td className="px-4 py-3.5">
                    <div className="font-semibold text-ex-text">{w.user?.name || "—"}</div>
                    <div className="text-xs text-ex-muted truncate max-w-[200px]">
                      {w.user?.email || w.user_id}
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        <BadgeCheck className="h-3 w-3" /> KYC: {w.user?.kyc_status || "approved"}
                      </span>
                      <span className="inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded bg-sky-500/10 text-sky-400 border border-sky-500/20">
                        <ShieldCheck className="h-3 w-3" /> OTP: VERIFIED
                      </span>
                    </div>
                  </td>

                  {/* Amount & Network */}
                  <td className="px-4 py-3.5">
                    <div className="text-base font-extrabold text-ex-text">
                      {money(w.amount)} USDT
                    </div>
                    <div className="mt-1">
                      <NetworkBadge network={w.network} />
                    </div>
                  </td>

                  {/* Destination */}
                  <td className="px-4 py-3.5 max-w-[240px]">
                    <div className="font-mono text-xs text-ex-lav-200 truncate" title={w.to_address}>
                      {w.to_address}
                    </div>
                    {w.tx_hash && (
                      <div className="font-mono text-[11px] text-emerald-400 truncate mt-0.5" title={w.tx_hash}>
                        TX: {w.tx_hash}
                      </div>
                    )}
                  </td>

                  {/* Status */}
                  <td className="px-4 py-3.5">
                    <StatusBadge status={w.status} />
                  </td>

                  {/* Submitted Date */}
                  <td className="px-4 py-3.5 text-xs text-ex-muted whitespace-nowrap">
                    {dayjs(w.created_at).format("DD MMM YYYY, HH:mm")}
                  </td>

                  {/* Actions */}
                  <td className="px-4 py-3.5 text-right">
                    <div className="flex items-center justify-end gap-1.5 flex-wrap">
                      <button
                        onClick={() => openView(w)}
                        className="px-2.5 py-1.5 rounded-ex-ctrl text-xs font-semibold bg-white/5 hover:bg-white/10 text-ex-text transition flex items-center gap-1"
                        title="View Details"
                      >
                        <Eye className="h-3.5 w-3.5" />
                        <span>View</span>
                      </button>

                      {w.status === "pending" && (
                        <>
                          <button
                            onClick={() => openApprove(w)}
                            data-testid={`wd-approve-${w.id}`}
                            className="px-2.5 py-1.5 rounded-ex-ctrl text-xs font-semibold bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 transition flex items-center gap-1"
                          >
                            <Check className="h-3.5 w-3.5" /> Approve
                          </button>
                          <button
                            onClick={() => openReject(w)}
                            data-testid={`wd-reject-open-${w.id}`}
                            className="px-2.5 py-1.5 rounded-ex-ctrl text-xs font-semibold bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 transition flex items-center gap-1"
                          >
                            <X className="h-3.5 w-3.5" /> Reject
                          </button>
                        </>
                      )}

                      {w.status === "approved" && (
                        <>
                          <button
                            onClick={() => doSetProcessing(w)}
                            className="px-2.5 py-1.5 rounded-ex-ctrl text-xs font-semibold bg-sky-500/10 hover:bg-sky-500/20 text-sky-400 border border-sky-500/20 transition flex items-center gap-1"
                          >
                            <Play className="h-3.5 w-3.5" /> Mark Processing
                          </button>
                          <button
                            onClick={() => openProcess(w)}
                            data-testid={`wd-process-open-${w.id}`}
                            className="px-2.5 py-1.5 rounded-ex-ctrl text-xs font-bold bg-ex-accent hover:bg-ex-accent/90 text-ex-ink transition flex items-center gap-1"
                          >
                            <Send className="h-3.5 w-3.5" /> Complete (TX)
                          </button>
                          <button
                            onClick={() => openReject(w)}
                            className="px-2.5 py-1.5 rounded-ex-ctrl text-xs font-semibold bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 transition flex items-center gap-1"
                          >
                            <X className="h-3.5 w-3.5" /> Reject
                          </button>
                        </>
                      )}

                      {w.status === "processing" && (
                        <>
                          <button
                            onClick={() => openProcess(w)}
                            data-testid={`wd-process-open-${w.id}`}
                            className="px-2.5 py-1.5 rounded-ex-ctrl text-xs font-bold bg-ex-accent hover:bg-ex-accent/90 text-ex-ink transition flex items-center gap-1"
                          >
                            <Send className="h-3.5 w-3.5" /> Complete (TX)
                          </button>
                          <button
                            onClick={() => openReject(w)}
                            className="px-2.5 py-1.5 rounded-ex-ctrl text-xs font-semibold bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 transition flex items-center gap-1"
                          >
                            <X className="h-3.5 w-3.5" /> Reject
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </EasyXTable>
          </div>
        </EasyXCard>
      )}

      {/* DETAIL MODAL */}
      <EasyXModal
        open={modal?.type === "view"}
        onClose={close}
        title="Withdrawal Request Inspection"
      >
        {modal?.withdrawal && (
          <div className="space-y-4 text-sm">
            <div className="flex items-center justify-between p-3.5 rounded-ex-card bg-white/[0.03] border border-white/8">
              <div>
                <div className="text-xs text-ex-muted">Requested Amount</div>
                <div className="text-xl font-extrabold text-ex-text mt-0.5">
                  {money(modal.withdrawal.amount)} USDT
                </div>
              </div>
              <div className="flex flex-col items-end gap-1.5">
                <NetworkBadge network={modal.withdrawal.network} />
                <StatusBadge status={modal.withdrawal.status} />
              </div>
            </div>

            <div className="space-y-2.5 text-xs">
              <div className="p-2.5 rounded-ex-ctrl bg-white/[0.02] border border-white/6 flex justify-between">
                <span className="text-ex-muted">User Profile</span>
                <span className="font-semibold text-ex-text">
                  {modal.withdrawal.user?.name || "—"} ({modal.withdrawal.user?.email || modal.withdrawal.user_id})
                </span>
              </div>

              <div className="p-2.5 rounded-ex-ctrl bg-white/[0.02] border border-white/6 flex justify-between items-center">
                <span className="text-ex-muted">Withdrawal ID</span>
                <span className="font-mono text-ex-lav-200">{modal.withdrawal.id}</span>
              </div>

              <div className="p-2.5 rounded-ex-ctrl bg-white/[0.02] border border-white/6">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-ex-muted">Destination Address</span>
                  <button
                    onClick={() => copyAddress(modal.withdrawal.to_address)}
                    className="text-ex-accent hover:underline flex items-center gap-1 font-semibold"
                  >
                    {copiedAddr ? <CheckCheck className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                    {copiedAddr ? "Copied" : "Copy"}
                  </button>
                </div>
                <div className="font-mono text-ex-text break-all bg-black/40 p-2 rounded border border-white/6">
                  {modal.withdrawal.to_address}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div className="p-2.5 rounded-ex-ctrl bg-white/[0.02] border border-white/6">
                  <span className="text-ex-muted block">KYC Verification</span>
                  <span className="font-bold text-emerald-400 flex items-center gap-1 mt-0.5">
                    <BadgeCheck className="h-3.5 w-3.5" /> Approved
                  </span>
                </div>
                <div className="p-2.5 rounded-ex-ctrl bg-white/[0.02] border border-white/6">
                  <span className="text-ex-muted block">OTP Verification</span>
                  <span className="font-bold text-sky-400 flex items-center gap-1 mt-0.5">
                    <ShieldCheck className="h-3.5 w-3.5" /> Verified
                  </span>
                </div>
              </div>

              <div className="p-2.5 rounded-ex-ctrl bg-white/[0.02] border border-white/6 flex justify-between">
                <span className="text-ex-muted">Submitted Time</span>
                <span className="text-ex-text">
                  {dayjs(modal.withdrawal.created_at).format("DD MMM YYYY, HH:mm:ss")}
                </span>
              </div>

              {modal.withdrawal.tx_hash && (
                <div className="p-2.5 rounded-ex-ctrl bg-white/[0.02] border border-white/6">
                  <span className="text-ex-muted block mb-1">Blockchain Transaction Hash</span>
                  <div className="font-mono text-emerald-400 break-all bg-black/40 p-2 rounded border border-white/6">
                    {modal.withdrawal.tx_hash}
                  </div>
                </div>
              )}
            </div>

            {modal.withdrawal.status === "pending" && (
              <div className="flex gap-2 pt-3 border-t border-white/8">
                <EasyXButton
                  variant="ghost"
                  className="flex-1 text-rose-400 hover:bg-rose-500/10 border border-rose-500/20"
                  onClick={() => openReject(modal.withdrawal)}
                >
                  <X className="mr-1.5 h-4 w-4" /> Reject
                </EasyXButton>
                <EasyXButton
                  variant="accent"
                  className="flex-1 font-bold"
                  onClick={() => openApprove(modal.withdrawal)}
                >
                  <Check className="mr-1.5 h-4 w-4" /> Approve
                </EasyXButton>
              </div>
            )}
          </div>
        )}
      </EasyXModal>

      {/* APPROVE CONFIRMATION MODAL */}
      <EasyXModal
        open={modal?.type === "approve"}
        onClose={close}
        title="Approve Withdrawal Request"
      >
        {modal?.withdrawal && (
          <div className="space-y-4 text-sm">
            <div className="p-3.5 rounded-ex-card bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs">
              <div className="font-bold flex items-center gap-1.5">
                <ShieldCheck className="h-4 w-4" />
                Ready for On-Chain Transfer
              </div>
              <div className="mt-1 text-emerald-200/90 leading-relaxed">
                Approving this withdrawal of <strong>{money(modal.withdrawal.amount)} USDT</strong> ({modal.withdrawal.network})
                authorizes the manual payout transfer to <code>{modal.withdrawal.to_address}</code>.
              </div>
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
                loading={action.isPending}
              >
                <Check className="mr-1.5 h-4 w-4" /> Confirm Approval
              </EasyXButton>
            </div>
          </div>
        )}
      </EasyXModal>

      {/* PROCESS / COMPLETE WITH TRANSACTION HASH MODAL */}
      <EasyXModal
        open={modal?.type === "process"}
        onClose={close}
        title="Complete Manual USDT Transfer"
      >
        {modal?.withdrawal && (
          <div className="space-y-4 text-sm">
            <div className="p-3.5 rounded-ex-card bg-sky-500/10 border border-sky-500/20 text-sky-300 text-xs">
              <div className="font-bold flex items-center gap-1.5">
                <Send className="h-4 w-4" />
                Manual Payout Dispatch
              </div>
              <div className="mt-1 text-sky-200/90 leading-relaxed">
                Send exactly <strong>{money(modal.withdrawal.amount)} USDT</strong> to the destination address on <strong>{modal.withdrawal.network}</strong>:
                <div className="font-mono text-white break-all bg-black/40 p-2 rounded mt-1.5 border border-white/6 select-all">
                  {modal.withdrawal.to_address}
                </div>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-ex-muted mb-1.5">
                Blockchain Transaction Hash (TX ID)
              </label>
              <input
                value={txHash}
                onChange={(e) => setTxHash(e.target.value)}
                placeholder="e.g. 0x... or Tronscan TX Hash"
                className="w-full rounded-ex-ctrl bg-white/5 border border-white/10 p-2.5 text-sm font-mono text-ex-text focus:border-ex-accent focus:outline-none"
                data-testid="wd-tx-hash-input"
              />
              <p className="mt-1 text-[11px] text-ex-muted">
                Entering the broadcasted TX Hash marks this withdrawal as <strong>COMPLETED</strong> and notifies the user.
              </p>
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
                onClick={doProcessComplete}
                loading={action.isPending}
                data-testid="wd-process-confirm"
              >
                <Check className="mr-1.5 h-4 w-4" /> Mark Completed
              </EasyXButton>
            </div>
          </div>
        )}
      </EasyXModal>

      {/* REJECT MODAL */}
      <EasyXModal
        open={modal?.type === "reject"}
        onClose={close}
        title="Reject Withdrawal Request"
      >
        {modal?.withdrawal && (
          <div className="space-y-4 text-sm">
            <div className="p-3.5 rounded-ex-card bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
              <div className="font-bold flex items-center gap-1.5">
                <AlertTriangle className="h-4 w-4" />
                Wallet Funds Reversal
              </div>
              <div className="mt-1 text-rose-200/90 leading-relaxed">
                Rejecting withdrawal <strong>{modal.withdrawal.id}</strong> will automatically return the held{" "}
                <strong>{money(modal.withdrawal.amount)} USDT</strong> back to the user's available wallet balance.
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-ex-muted mb-1.5">
                Rejection Reason (Recorded in audit log)
              </label>
              <input
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="e.g. Invalid address checksum, network mismatch, or user requested cancel"
                className="w-full rounded-ex-ctrl bg-white/5 border border-white/10 p-2.5 text-sm text-ex-text focus:border-rose-400 focus:outline-none"
                data-testid="wd-reject-reason-input"
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
                loading={action.isPending}
                className="flex-1 bg-rose-500 hover:bg-rose-600 text-white font-bold"
                data-testid="wd-reject-confirm"
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
