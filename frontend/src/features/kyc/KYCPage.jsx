import React, { useEffect, useRef, useState } from "react";
import { ShieldCheck, UploadCloud, CheckCircle2, Clock, XCircle, FileImage, Camera, Lightbulb } from "lucide-react";
import { toast } from "sonner";

import { useKyc, useSubmitKyc } from "@/features/dashboard/api";
import { apiError } from "@/lib/api";
import {
  PageHeading,
  EasyXCard,
  EasyXButton,
  EasyXLoader,
  EasyXStatusBadge,
} from "@/design/EasyX";

const ID_TYPES = [
  { value: "aadhaar", label: "Aadhaar" },
  { value: "national_id", label: "National ID" },
  { value: "passport", label: "Passport" },
  { value: "other", label: "Other" },
];

const MAX_BYTES = 5 * 1024 * 1024;
const ALLOWED = ["image/jpeg", "image/png", "image/webp", "application/pdf"];

function FileField({ label, file, onPick, testId, hint }) {
  const inputRef = useRef(null);
  const [preview, setPreview] = useState(null);

  // Instant photo preview for images (object URL, revoked on change/unmount).
  useEffect(() => {
    if (file && file.type && file.type.startsWith("image/")) {
      const url = URL.createObjectURL(file);
      setPreview(url);
      return () => URL.revokeObjectURL(url);
    }
    setPreview(null);
    return undefined;
  }, [file]);

  return (
    <div>
      <div className="text-xs text-ex-muted mb-1">{label}</div>
      <div className="flex items-center gap-3">
        {/* Preview thumbnail */}
        <div className="relative grid h-16 w-16 shrink-0 place-items-center overflow-hidden rounded-ex border border-white/10 bg-white/[0.03]">
          {preview ? (
            <img src={preview} alt="preview" className="h-full w-full object-cover" data-testid={`${testId}-preview`} />
          ) : file ? (
            <FileImage className="h-6 w-6 text-ex-lav-300" />
          ) : (
            <Camera className="h-6 w-6 text-ex-muted" />
          )}
        </div>
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          data-testid={testId}
          className="flex flex-1 items-center gap-3 rounded-ex-ctrl border border-dashed border-white/15 bg-white/[0.03] px-4 py-3 text-left transition hover:border-ex-accent/60"
        >
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-ex-lav-400/15 text-ex-lav-300">
            <UploadCloud className="h-5 w-5" />
          </span>
          <span className="min-w-0">
            <span className="block truncate text-sm text-ex-text">
              {file ? file.name : "Click to upload"}
            </span>
            <span className="block text-[11px] text-ex-muted">{file ? "Tap to replace" : hint}</span>
          </span>
        </button>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,application/pdf"
        className="hidden"
        onChange={(e) => onPick(e.target.files?.[0] || null)}
      />
    </div>
  );
}

const SELFIE_TIPS = [
  "Use good, even lighting — face the light source",
  "Make sure your whole face is clearly visible",
  "Remove hats, sunglasses or anything covering your face",
  "Keep a plain background and hold the camera steady",
];

function SelfieTips() {
  return (
    <div className="rounded-ex-ctrl border border-ex-lav-400/25 bg-ex-lav-400/[0.07] p-3" data-testid="kyc-selfie-tips">
      <div className="flex items-center gap-1.5 text-xs font-semibold text-ex-lav-200">
        <Lightbulb className="h-3.5 w-3.5" /> Tips for an approvable selfie
      </div>
      <ul className="mt-2 space-y-1">
        {SELFIE_TIPS.map((t) => (
          <li key={t} className="flex items-start gap-2 text-[11px] text-ex-muted">
            <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-ex-lav-300" />
            {t}
          </li>
        ))}
      </ul>
    </div>
  );
}

function StatusBanner({ kyc }) {
  const s = kyc.status;
  if (s === "approved") {
    return (
      <div className="flex items-start gap-3 rounded-ex border border-emerald-500/30 bg-emerald-500/10 p-4" data-testid="kyc-status-approved">
        <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-300" />
        <div>
          <div className="text-sm font-semibold text-emerald-200">Identity verified</div>
          <div className="text-xs text-emerald-200/70">Your KYC is approved. Withdrawals are unlocked.</div>
        </div>
      </div>
    );
  }
  if (s === "pending") {
    return (
      <div className="flex items-start gap-3 rounded-ex border border-amber-500/30 bg-amber-500/10 p-4" data-testid="kyc-status-pending">
        <Clock className="h-5 w-5 shrink-0 text-amber-300" />
        <div>
          <div className="text-sm font-semibold text-amber-200">Under review</div>
          <div className="text-xs text-amber-200/70">We're verifying your documents. This usually takes a short while.</div>
        </div>
      </div>
    );
  }
  if (s === "rejected") {
    return (
      <div className="flex items-start gap-3 rounded-ex border border-red-500/30 bg-red-500/10 p-4" data-testid="kyc-status-rejected">
        <XCircle className="h-5 w-5 shrink-0 text-red-300" />
        <div>
          <div className="text-sm font-semibold text-red-200">Verification rejected</div>
          <div className="text-xs text-red-200/80">{kyc.reject_reason || "Please resubmit with clearer documents."}</div>
        </div>
      </div>
    );
  }
  return null;
}

export default function KYCPage() {
  const { data: kyc, isLoading } = useKyc();
  const submitKyc = useSubmitKyc();

  const [idType, setIdType] = useState("aadhaar");
  const [idNumber, setIdNumber] = useState("");
  const [idDoc, setIdDoc] = useState(null);
  const [selfie, setSelfie] = useState(null);

  const validateFile = (f) => {
    if (!f) return "";
    if (!ALLOWED.includes(f.type)) return "Only JPG, PNG, WebP or PDF allowed.";
    if (f.size > MAX_BYTES) return "File must be 5 MB or smaller.";
    return "";
  };

  const idDocError = validateFile(idDoc);
  const selfieError = validateFile(selfie);
  const canSubmit = idType && idDoc && selfie && !idDocError && !selfieError && !submitKyc.isPending;

  const pickId = (f) => {
    const err = validateFile(f);
    if (err) { toast.error(err); return; }
    setIdDoc(f);
  };
  const pickSelfie = (f) => {
    const err = validateFile(f);
    if (err) { toast.error(err); return; }
    setSelfie(f);
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!canSubmit) return;
    try {
      await submitKyc.mutateAsync({ idType, idNumber: idNumber.trim() || null, idDocument: idDoc, selfie });
      toast.success("KYC submitted — pending review");
      setIdNumber(""); setIdDoc(null); setSelfie(null);
    } catch (err) {
      toast.error(apiError(err, "Could not submit KYC"));
    }
  };

  const canSubmitForm = kyc && (kyc.status === "none" || kyc.status === "rejected");

  return (
    <div data-testid="kyc-page">
      <PageHeading
        title="Identity Verification (KYC)"
        subtitle="Verify your identity to unlock withdrawals. KYC is not required to invest."
        icon={ShieldCheck}
        actions={kyc && kyc.status !== "none" ? <EasyXStatusBadge status={kyc.status} /> : null}
      />

      {isLoading || !kyc ? (
        <EasyXLoader />
      ) : (
        <div className="mt-5 max-w-2xl space-y-4">
          {kyc.status !== "none" && <StatusBanner kyc={kyc} />}

          {canSubmitForm ? (
            <EasyXCard>
              <div className="text-sm font-semibold text-ex-text">
                {kyc.status === "rejected" ? "Resubmit your documents" : "Submit your documents"}
              </div>
              <p className="mt-1 text-xs text-ex-muted">
                Upload a clear photo of your government ID and a selfie. Your documents are private
                and only visible to our verification team.
              </p>

              <form onSubmit={submit} className="mt-4 space-y-4" data-testid="kyc-form">
                <div>
                  <label className="text-xs text-ex-muted">ID type</label>
                  <select
                    value={idType}
                    onChange={(e) => setIdType(e.target.value)}
                    data-testid="kyc-id-type"
                    className="mt-1 w-full rounded-ex-ctrl bg-white/5 border border-white/10 px-3 py-2.5 text-sm text-ex-text focus:border-ex-accent focus:outline-none"
                  >
                    {ID_TYPES.map((t) => (
                      <option key={t.value} value={t.value} className="bg-[#17161d]">{t.label}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-xs text-ex-muted">ID number <span className="text-white/40">(optional)</span></label>
                  <input
                    type="text"
                    value={idNumber}
                    onChange={(e) => setIdNumber(e.target.value)}
                    placeholder="e.g. 1234 5678 9012"
                    data-testid="kyc-id-number"
                    className="mt-1 w-full rounded-ex-ctrl bg-white/5 border border-white/10 px-3 py-2.5 text-sm text-ex-text placeholder:text-ex-muted/60 focus:border-ex-accent focus:outline-none"
                  />
                  <p className="mt-1 text-[11px] text-ex-muted">Stored encrypted — never shown to anyone else.</p>
                </div>

                <FileField label="Government ID (Aadhaar / National ID / Passport)" file={idDoc} onPick={pickId} testId="kyc-id-upload" hint="JPG, PNG, WebP or PDF · max 5 MB" />
                <SelfieTips />
                <FileField label="Selfie" file={selfie} onPick={pickSelfie} testId="kyc-selfie-upload" hint="A clear photo of your face · max 5 MB" />

                <EasyXButton type="submit" className="w-full" disabled={!canSubmit} loading={submitKyc.isPending} data-testid="kyc-submit">
                  {kyc.status === "rejected" ? "Resubmit for review" : "Submit for review"}
                </EasyXButton>
              </form>
            </EasyXCard>
          ) : (
            <EasyXCard>
              <p className="text-sm text-ex-muted">
                {kyc.status === "pending"
                  ? "Your documents are under review. You'll be notified once a decision is made."
                  : "Your identity is verified. No further action needed."}
              </p>
            </EasyXCard>
          )}
        </div>
      )}
    </div>
  );
}
