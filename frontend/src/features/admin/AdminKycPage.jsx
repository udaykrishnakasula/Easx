import React, { useEffect, useState } from "react";
import { BadgeCheck, FileImage, Check, X } from "lucide-react";
import { toast } from "sonner";
import dayjs from "dayjs";

import {
  useAdminKyc,
  useApproveKyc,
  useRejectKyc,
  fetchAdminKycDocUrl,
} from "@/features/admin/adminApi";
import { apiError } from "@/lib/api";
import {
  PageHeading,
  EasyXCard,
  EasyXButton,
  EasyXLoader,
  EasyXStatusBadge,
  EasyXEmptyState,
} from "@/design/EasyX";

const FILTERS = ["pending", "approved", "rejected", "all"];

function DocThumb({ docId, label }) {
  const [url, setUrl] = useState(null);
  const [err, setErr] = useState(false);
  useEffect(() => {
    let active = true;
    let objectUrl = null;
    fetchAdminKycDocUrl(docId)
      .then((u) => { if (active) { objectUrl = u; setUrl(u); } })
      .catch(() => { if (active) setErr(true); });
    return () => { active = false; if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [docId]);

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="text-[11px] text-ex-muted capitalize">{label.replace("_", " ")}</div>
      {err ? (
        <div className="grid h-28 w-28 place-items-center rounded-ex border border-white/10 bg-white/5 text-ex-muted">
          <FileImage className="h-6 w-6" />
        </div>
      ) : url ? (
        <a href={url} target="_blank" rel="noreferrer">
          <img src={url} alt={label} className="h-28 w-28 rounded-ex border border-white/10 object-cover" data-testid={`kyc-doc-${docId}`} />
        </a>
      ) : (
        <div className="grid h-28 w-28 place-items-center rounded-ex border border-white/10 bg-white/5">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-ex-accent border-t-transparent" />
        </div>
      )}
    </div>
  );
}

function KycRow({ rec }) {
  const approve = useApproveKyc();
  const reject = useRejectKyc();
  const [reason, setReason] = useState("");
  const [showReject, setShowReject] = useState(false);
  const isPending = rec.status === "pending";

  const doApprove = async () => {
    try {
      await approve.mutateAsync({ id: rec.id });
      toast.success(`KYC approved for ${rec.user_email}`);
    } catch (e) { toast.error(apiError(e, "Could not approve")); }
  };
  const doReject = async () => {
    if (reason.trim().length < 3) { toast.error("Please enter a rejection reason."); return; }
    try {
      await reject.mutateAsync({ id: rec.id, reason: reason.trim() });
      toast.success("KYC rejected");
      setShowReject(false); setReason("");
    } catch (e) { toast.error(apiError(e, "Could not reject")); }
  };

  return (
    <EasyXCard className="space-y-3" data-testid={`admin-kyc-row-${rec.id}`}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="text-sm font-semibold text-ex-text">{rec.user_name || "User"}</div>
          <div className="text-[11px] text-ex-muted">{rec.user_email}</div>
          <div className="mt-1 text-[11px] text-ex-muted">
            ID type: <span className="capitalize text-ex-text">{rec.id_type || "—"}</span>
            {rec.id_number_present && <span className="ml-2 text-emerald-300">· ID number on file (encrypted)</span>}
          </div>
          <div className="text-[11px] text-ex-muted">Submitted {rec.submitted_at ? dayjs(rec.submitted_at).format("DD MMM YYYY, HH:mm") : "—"}</div>
        </div>
        <EasyXStatusBadge status={rec.status} />
      </div>

      <div className="flex flex-wrap gap-4">
        {rec.documents.map((d) => (
          <DocThumb key={d.id} docId={d.id} label={d.doc_type} />
        ))}
      </div>

      {rec.status === "rejected" && rec.reject_reason && (
        <div className="rounded-ex-ctrl border border-red-500/30 bg-red-500/10 px-3 py-2 text-[11px] text-red-200">
          Rejected: {rec.reject_reason}
        </div>
      )}

      {isPending && (
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <EasyXButton variant="accent" onClick={doApprove} loading={approve.isPending} data-testid={`admin-kyc-approve-${rec.id}`}>
            <Check className="mr-1.5 h-4 w-4" /> Approve
          </EasyXButton>
          {!showReject ? (
            <EasyXButton variant="ghost" onClick={() => setShowReject(true)} data-testid={`admin-kyc-reject-open-${rec.id}`}>
              <X className="mr-1.5 h-4 w-4" /> Reject
            </EasyXButton>
          ) : (
            <div className="flex flex-1 items-center gap-2 min-w-[240px]">
              <input
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Reason for rejection"
                data-testid={`admin-kyc-reject-reason-${rec.id}`}
                className="flex-1 rounded-ex-ctrl bg-white/5 border border-white/10 px-3 py-2 text-sm text-ex-text placeholder:text-ex-muted/60 focus:border-ex-accent focus:outline-none"
              />
              <EasyXButton variant="ghost" onClick={doReject} loading={reject.isPending} data-testid={`admin-kyc-reject-confirm-${rec.id}`}>
                Confirm
              </EasyXButton>
            </div>
          )}
        </div>
      )}
    </EasyXCard>
  );
}

export default function AdminKycPage() {
  const [filter, setFilter] = useState("pending");
  const { data: list, isLoading } = useAdminKyc(filter === "all" ? undefined : filter);

  return (
    <div data-testid="admin-kyc-page">
      <PageHeading title="KYC Review" subtitle="Review and verify user identity submissions." icon={BadgeCheck} />

      <div className="mt-4 inline-flex rounded-ex-ctrl bg-white/5 p-1">
        {FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            data-testid={`admin-kyc-filter-${f}`}
            data-active={filter === f ? "true" : "false"}
            className={`px-4 py-2 rounded-ex-ctrl text-sm font-medium capitalize transition ${
              filter === f ? "bg-ex-accent text-ex-ink shadow-ex-btn" : "text-ex-muted hover:text-ex-text"
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {isLoading ? (
        <EasyXLoader />
      ) : !list || list.length === 0 ? (
        <div className="mt-5">
          <EasyXEmptyState icon={BadgeCheck} title="Nothing here" note={`No ${filter} KYC submissions.`} />
        </div>
      ) : (
        <div className="mt-5 grid grid-cols-1 gap-4" data-testid="admin-kyc-list">
          {list.map((rec) => (
            <KycRow key={rec.id} rec={rec} />
          ))}
        </div>
      )}
    </div>
  );
}
