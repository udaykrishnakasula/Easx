import React, { useEffect, useState } from "react";
import {
  BadgeCheck,
  FileImage,
  Check,
  X,
  Eye,
  Calendar,
  User,
  ShieldCheck,
  AlertTriangle,
  ZoomIn,
  Download,
} from "lucide-react";
import { toast } from "sonner";
import dayjs from "dayjs";

import {
  useAdminKyc,
  useApproveKyc,
  useRejectKyc,
  fetchAdminKycDocUrl,
} from "@/admin/adminApi";
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
  { key: "", label: "All Submissions" },
];

function StatusPill({ status }) {
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

function DocPreview({ docId, label, onExpand }) {
  const [url, setUrl] = useState(null);
  const [err, setErr] = useState(false);

  useEffect(() => {
    let active = true;
    let objectUrl = null;
    fetchAdminKycDocUrl(docId)
      .then((u) => {
        if (active) {
          objectUrl = u;
          setUrl(u);
        }
      })
      .catch(() => {
        if (active) setErr(true);
      });
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [docId]);

  const displayLabel =
    label === "id_front"
      ? "Aadhaar / ID Front"
      : label === "id_back"
      ? "Aadhaar Back"
      : label === "selfie"
      ? "Live Selfie Photo"
      : label.replace("_", " ");

  return (
    <div className="flex flex-col gap-1.5 min-w-[160px] flex-1 sm:flex-initial">
      <div className="text-xs font-semibold text-ex-muted flex items-center justify-between">
        <span className="capitalize">{displayLabel}</span>
      </div>

      {err ? (
        <div className="grid h-36 w-full sm:w-48 place-items-center rounded-ex-ctrl border border-white/10 bg-white/5 text-ex-muted text-xs p-2 text-center">
          <FileImage className="h-6 w-6 mb-1" />
          <span>Encrypted document unavailable</span>
        </div>
      ) : url ? (
        <div className="relative group rounded-ex-ctrl overflow-hidden border border-white/10 bg-black/40 h-36 w-full sm:w-48">
          <img
            src={url}
            alt={label}
            className="h-full w-full object-cover transition duration-300 group-hover:scale-105"
            data-testid={`kyc-doc-${docId}`}
          />
          <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
            <button
              onClick={() => onExpand(url, displayLabel)}
              className="p-2 rounded-full bg-white/20 hover:bg-white/30 text-white transition"
              title="Zoom In"
            >
              <ZoomIn className="h-4 w-4" />
            </button>
            <a
              href={url}
              target="_blank"
              rel="noreferrer"
              className="p-2 rounded-full bg-white/20 hover:bg-white/30 text-white transition"
              title="Open full resolution"
            >
              <Eye className="h-4 w-4" />
            </a>
          </div>
        </div>
      ) : (
        <div className="grid h-36 w-full sm:w-48 place-items-center rounded-ex-ctrl border border-white/10 bg-white/5">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-ex-accent border-t-transparent" />
        </div>
      )}
    </div>
  );
}

export default function AdminKycPage() {
  const [filter, setFilter] = useState("pending");
  const { data: list, isLoading } = useAdminKyc(filter || undefined);
  const approve = useApproveKyc();
  const reject = useRejectKyc();

  const [modal, setModal] = useState(null); // { type: 'reject', record }
  const [rejectReason, setRejectReason] = useState("");
  const [lightbox, setLightbox] = useState(null); // { url, title }

  const openReject = (rec) => {
    setModal({ type: "reject", record: rec });
    setRejectReason("");
  };

  const close = () => setModal(null);

  const doApprove = async (rec) => {
    try {
      await approve.mutateAsync({ id: rec.id });
      toast.success(`KYC identity verification approved for ${rec.user_name || rec.user_email}`);
    } catch (e) {
      toast.error(apiError(e, "Could not approve KYC submission"));
    }
  };

  const doReject = async () => {
    if (rejectReason.trim().length < 3) {
      toast.error("Please enter a specific rejection reason (min 3 characters).");
      return;
    }
    try {
      await reject.mutateAsync({ id: modal.record.id, reason: rejectReason.trim() });
      toast.success("KYC submission rejected. Reason logged and user notified.");
      close();
    } catch (e) {
      toast.error(apiError(e, "Could not reject KYC submission"));
    }
  };

  const kycRecords = list || [];

  return (
    <div className="space-y-6" data-testid="admin-kyc-page">
      <PageHeading
        title="KYC & Identity Verification"
        subtitle="Review, inspect, and verify submitted National IDs, Aadhaar cards, and live selfie photos."
        icon={BadgeCheck}
      />

      {/* Filter Bar */}
      <div className="flex flex-wrap gap-2" data-testid="admin-kyc-filters">
        {FILTERS.map((f) => (
          <button
            key={f.key || "all"}
            onClick={() => setFilter(f.key)}
            data-testid={`admin-kyc-filter-${f.key || "all"}`}
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
      {isLoading ? (
        <EasyXLoader />
      ) : kycRecords.length === 0 ? (
        <EasyXEmptyState
          icon={BadgeCheck}
          title="No KYC submissions"
          description="No identity verification submissions match the selected filter."
        />
      ) : (
        <div className="space-y-4" data-testid="admin-kyc-list">
          {kycRecords.map((rec) => (
            <EasyXCard
              key={rec.id}
              className="p-5 border border-white/8 space-y-4 hover:border-white/16 transition-all"
              data-testid={`admin-kyc-row-${rec.id}`}
            >
              {/* Header and User Details */}
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-base font-bold text-ex-text">
                      {rec.user_name || "Investor"}
                    </span>
                    <StatusPill status={rec.status} />
                  </div>
                  <div className="text-xs text-ex-muted flex flex-wrap items-center gap-x-3 gap-y-1">
                    <span>{rec.user_email}</span>
                    <span>·</span>
                    <span>
                      ID Type: <strong className="text-ex-text uppercase">{rec.id_type || "National ID"}</strong>
                    </span>
                    {rec.id_number_present && (
                      <>
                        <span>·</span>
                        <span className="text-emerald-400 font-medium">ID Number on File (Encrypted)</span>
                      </>
                    )}
                  </div>
                  <div className="text-[11px] text-ex-muted">
                    Submitted: {rec.submitted_at ? dayjs(rec.submitted_at).format("DD MMM YYYY, HH:mm:ss") : "—"}
                  </div>
                </div>

                {/* Status-dependent Action Buttons */}
                {rec.status === "pending" && (
                  <div className="flex items-center gap-2 shrink-0">
                    <EasyXButton
                      variant="accent"
                      onClick={() => doApprove(rec)}
                      loading={approve.isPending}
                      data-testid={`admin-kyc-approve-${rec.id}`}
                      className="font-bold text-xs h-9"
                    >
                      <Check className="mr-1.5 h-3.5 w-3.5" /> Approve KYC
                    </EasyXButton>
                    <EasyXButton
                      variant="ghost"
                      onClick={() => openReject(rec)}
                      data-testid={`admin-kyc-reject-open-${rec.id}`}
                      className="font-bold text-xs h-9 text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 border border-rose-500/20"
                    >
                      <X className="mr-1.5 h-3.5 w-3.5" /> Reject
                    </EasyXButton>
                  </div>
                )}
              </div>

              {/* Document & Live Camera Selfie Inspection Section */}
              <div className="p-3.5 rounded-ex-ctrl bg-black/20 border border-white/6 space-y-2">
                <div className="text-xs font-semibold text-ex-muted flex items-center justify-between">
                  <span>Submitted Documents &amp; Live Camera Selfie</span>
                  <span className="text-[10px] text-ex-lav-300 font-mono">Manual Verification</span>
                </div>

                <div className="flex flex-wrap gap-4 pt-1">
                  {rec.documents && rec.documents.length > 0 ? (
                    rec.documents.map((d) => (
                      <DocPreview
                        key={d.id}
                        docId={d.id}
                        label={d.doc_type === "selfie" ? "Live Camera Selfie" : d.doc_type}
                        onExpand={(url, title) => setLightbox({ url, title })}
                      />
                    ))
                  ) : (
                    <div className="text-xs text-ex-muted italic">No documents attached.</div>
                  )}
                </div>
              </div>

              {/* Rejection Reason display if rejected */}
              {rec.status === "rejected" && rec.reject_reason && (
                <div className="rounded-ex-ctrl border border-rose-500/20 bg-rose-500/10 p-3 text-xs text-rose-300 flex items-start gap-2">
                  <AlertTriangle className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
                  <div>
                    <span className="font-bold">Rejection Reason:</span> {rec.reject_reason}
                  </div>
                </div>
              )}
            </EasyXCard>
          ))}
        </div>
      )}

      {/* REJECT MODAL */}
      <EasyXModal
        open={modal?.type === "reject"}
        onClose={close}
        title="Reject KYC Submission"
      >
        {modal?.record && (
          <div className="space-y-4 text-sm">
            <div className="p-3.5 rounded-ex-card bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
              <div className="font-bold flex items-center gap-1.5">
                <AlertTriangle className="h-4 w-4" />
                Mandatory Rejection Reason
              </div>
              <div className="mt-1 text-rose-200/90 leading-relaxed">
                Rejecting the identity verification for <strong>{modal.record.user_name || modal.record.user_email}</strong>{" "}
                requires a clear explanation so the investor can correct and re-upload valid documents.
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-ex-muted mb-1.5">
                Rejection Reason (Sent to User &amp; Audit Log)
              </label>
              <textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="e.g. ID photo is blurry/unreadable, Selfie does not match National ID, Expired document"
                rows={3}
                className="w-full rounded-ex-ctrl bg-white/5 border border-white/10 p-3 text-sm text-ex-text placeholder:text-ex-muted/50 focus:border-rose-400 focus:outline-none"
                data-testid={`admin-kyc-reject-reason-${modal.record.id}`}
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
                data-testid={`admin-kyc-reject-confirm-${modal.record.id}`}
              >
                <X className="mr-1.5 h-4 w-4" /> Confirm Rejection
              </EasyXButton>
            </div>
          </div>
        )}
      </EasyXModal>

      {/* LIGHTBOX MODAL */}
      <EasyXModal
        open={Boolean(lightbox)}
        onClose={() => setLightbox(null)}
        title={lightbox?.title || "Document Inspection"}
      >
        {lightbox && (
          <div className="space-y-3">
            <div className="rounded-ex-ctrl overflow-hidden bg-black/80 flex items-center justify-center max-h-[70vh]">
              <img src={lightbox.url} alt={lightbox.title} className="max-h-[68vh] w-auto object-contain" />
            </div>
            <div className="flex justify-end">
              <a
                href={lightbox.url}
                target="_blank"
                rel="noreferrer"
                className="text-xs text-ex-accent hover:underline flex items-center gap-1 font-semibold"
              >
                <Eye className="h-3.5 w-3.5" /> View original full-size image in new tab
              </a>
            </div>
          </div>
        )}
      </EasyXModal>
    </div>
  );
}
