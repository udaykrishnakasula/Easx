import React, { useEffect, useRef, useState } from "react";
import { ShieldCheck, UploadCloud, CheckCircle2, Clock, XCircle, FileImage, Camera, Lightbulb } from "lucide-react";
import { toast } from "sonner";

import { useKyc, useSubmitKyc } from "@/user/api";
import { apiError } from "@/shared/lib/api";
import {
  PageHeading,
  EasyXCard,
  EasyXButton,
  EasyXLoader,
  EasyXStatusBadge,
} from "@/design/EasyX";
import KycCameraCapture from "@/user/components/KycCameraCapture";

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
              {file ? file.name : "Click to select ID document"}
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
  "Use good, even lighting — face the light source directly",
  "Make sure your whole face is clearly visible inside the oval guide",
  "Remove hats, sunglasses, or anything covering your facial features",
  "Hold your phone/device steady at eye level",
];

function SelfieTips() {
  return (
    <div className="rounded-ex-ctrl border border-ex-lav-400/25 bg-ex-lav-400/[0.07] p-3" data-testid="kyc-selfie-tips">
      <div className="flex items-center gap-1.5 text-xs font-semibold text-ex-lav-200">
        <Lightbulb className="h-3.5 w-3.5" /> Guidelines for clear identity photo
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
          <div className="text-xs text-emerald-200/70">Your KYC verification is approved by the admin. Withdrawals are unlocked.</div>
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
          <div className="text-xs text-amber-200/70">Your ID documents and camera selfie are pending manual admin review.</div>
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
          <div className="text-xs text-red-200/80">{kyc.reject_reason || "Please resubmit with clearer documents and live camera photo."}</div>
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
  
  // Single document for non-Aadhaar IDs (National ID, Passport, Other)
  const [idDoc, setIdDoc] = useState(null);

  // Two separate documents specifically for Aadhaar
  const [idFrontDoc, setIdFrontDoc] = useState(null);
  const [idBackDoc, setIdBackDoc] = useState(null);

  // Live camera selfie blob (strictly camera-based)
  const [selfieBlob, setSelfieBlob] = useState(null);

  const validateFile = (f) => {
    if (!f) return "";
    if (!ALLOWED.includes(f.type)) return "Only JPG, PNG, WebP or PDF allowed.";
    if (f.size > MAX_BYTES) return "File must be 5 MB or smaller.";
    return "";
  };

  const isAadhaar = idType === "aadhaar";

  const idDocError = !isAadhaar ? validateFile(idDoc) : "";
  const idFrontError = isAadhaar ? validateFile(idFrontDoc) : "";
  const idBackError = isAadhaar ? validateFile(idBackDoc) : "";

  const hasValidDocs = isAadhaar
    ? Boolean(idFrontDoc && !idFrontError && idBackDoc && !idBackError)
    : Boolean(idDoc && !idDocError);

  const canSubmit = Boolean(idType && hasValidDocs && selfieBlob && !submitKyc.isPending);

  const pickSingleId = (f) => {
    const err = validateFile(f);
    if (err) { toast.error(err); return; }
    setIdDoc(f);
  };

  const pickFrontId = (f) => {
    const err = validateFile(f);
    if (err) { toast.error(err); return; }
    setIdFrontDoc(f);
  };

  const pickBackId = (f) => {
    const err = validateFile(f);
    if (err) { toast.error(err); return; }
    setIdBackDoc(f);
  };

  const handleCaptureComplete = (blob) => {
    setSelfieBlob(blob);
    toast.success("Live selfie photo captured");
  };

  const handleCameraReset = () => {
    setSelfieBlob(null);
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!canSubmit) {
      if (isAadhaar) {
        if (!idFrontDoc) {
          toast.error("Please upload Aadhaar Front Side.");
          return;
        }
        if (!idBackDoc) {
          toast.error("Please upload Aadhaar Back Side.");
          return;
        }
      } else {
        if (!idDoc) {
          toast.error("Please upload your government ID document.");
          return;
        }
      }
      if (!selfieBlob) {
        toast.error("Please take a live selfie with your camera before submitting.");
        return;
      }
      return;
    }

    try {
      if (isAadhaar) {
        await submitKyc.mutateAsync({
          idType,
          idNumber: idNumber.trim() || null,
          idFrontDocument: idFrontDoc,
          idBackDocument: idBackDoc,
          selfie: selfieBlob,
        });
      } else {
        await submitKyc.mutateAsync({
          idType,
          idNumber: idNumber.trim() || null,
          idDocument: idDoc,
          selfie: selfieBlob,
        });
      }
      toast.success("KYC submitted — pending admin review");
      setIdNumber("");
      setIdDoc(null);
      setIdFrontDoc(null);
      setIdBackDoc(null);
      setSelfieBlob(null);
    } catch (err) {
      toast.error(apiError(err, "Could not submit KYC"));
    }
  };

  const canSubmitForm = kyc && (kyc.status === "none" || kyc.status === "rejected");

  return (
    <div data-testid="kyc-page">
      <PageHeading
        title="Identity Verification (KYC)"
        subtitle="Verify your identity with government ID and camera photo to unlock withdrawals."
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
                {kyc.status === "rejected" ? "Resubmit your verification" : "Submit your verification"}
              </div>
              <p className="mt-1 text-xs text-ex-muted">
                Provide your government ID document and take a direct photo with your device's camera.
                The admin will review and verify your identity manually.
              </p>

              <form onSubmit={submit} className="mt-4 space-y-4" data-testid="kyc-form">
                <div>
                  <label className="text-xs text-ex-muted">ID type</label>
                  <select
                    value={idType}
                    onChange={(e) => {
                      setIdType(e.target.value);
                    }}
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
                  <p className="mt-1 text-[11px] text-ex-muted">Stored encrypted — only visible to the compliance admin.</p>
                </div>

                {/* Aadhaar requires two separate document uploads: Front Side and Back Side */}
                {isAadhaar ? (
                  <div className="space-y-3.5" data-testid="aadhaar-upload-section">
                    <FileField
                      label="Aadhaar Front Side"
                      file={idFrontDoc}
                      onPick={pickFrontId}
                      testId="kyc-id-front-upload"
                      hint="JPG, PNG, WebP or PDF · max 5 MB"
                    />

                    <FileField
                      label="Aadhaar Back Side"
                      file={idBackDoc}
                      onPick={pickBackId}
                      testId="kyc-id-back-upload"
                      hint="JPG, PNG, WebP or PDF · max 5 MB"
                    />
                  </div>
                ) : (
                  <FileField
                    label="Government ID (National ID / Passport)"
                    file={idDoc}
                    onPick={pickSingleId}
                    testId="kyc-id-upload"
                    hint="JPG, PNG, WebP or PDF · max 5 MB"
                  />
                )}

                <SelfieTips />

                {/* Direct Camera-Only Selfie */}
                <KycCameraCapture
                  onCaptureComplete={handleCaptureComplete}
                  onReset={handleCameraReset}
                  disabled={submitKyc.isPending}
                />

                <EasyXButton
                  type="submit"
                  className="w-full"
                  disabled={!canSubmit}
                  loading={submitKyc.isPending}
                  data-testid="kyc-submit"
                >
                  {kyc.status === "rejected" ? "Resubmit for manual review" : "Submit for manual review"}
                </EasyXButton>
              </form>
            </EasyXCard>
          ) : (
            <EasyXCard>
              <p className="text-sm text-ex-muted">
                {kyc.status === "pending"
                  ? "Your documents and selfie photo are under manual admin review. You'll be notified once reviewed."
                  : "Your identity is verified. No further action needed."}
              </p>
            </EasyXCard>
          )}
        </div>
      )}
    </div>
  );
}
