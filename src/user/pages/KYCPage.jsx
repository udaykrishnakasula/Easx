import React, { useEffect, useRef, useState, useMemo } from "react";
import {
  ShieldCheck,
  UploadCloud,
  CheckCircle2,
  Clock,
  XCircle,
  FileImage,
  Camera,
  Lightbulb,
  AlertCircle,
  Check,
  Trash2,
  FileText,
  FileCheck,
  CreditCard,
} from "lucide-react";
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
  { value: "aadhaar", label: "Aadhaar Card (India)", placeholder: "e.g. 1234 5678 9012", helper: "12-digit unique Aadhaar number (Front & Back required)" },
  { value: "national_id", label: "National ID Card", placeholder: "e.g. ID-894729104", helper: "Official government-issued national identity number" },
  { value: "passport", label: "International Passport", placeholder: "e.g. A1234567", helper: "6 to 9 alphanumeric characters" },
  { value: "driving_license", label: "Driver's License", placeholder: "e.g. DL-1420110012345", helper: "Official state/national driver's license number" },
  { value: "other", label: "Other Government ID", placeholder: "e.g. GOV-98765432", helper: "4 to 32 alphanumeric characters" },
];

const MAX_BYTES = 5 * 1024 * 1024; // 5 MB
const MIN_BYTES = 100; // 100 Bytes
const ALLOWED_MIME_TYPES = ["image/jpeg", "image/jpg", "image/png", "image/webp", "application/pdf"];
const ALLOWED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp", ".pdf"];

/** Format bytes to human readable format */
function formatBytes(bytes) {
  if (!bytes || bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

/** Validate document file on client side */
function validateFileObject(f) {
  if (!f) return null;
  const mime = f.type ? f.type.toLowerCase() : "";
  const name = f.name ? f.name.toLowerCase() : "";
  const hasValidExt = ALLOWED_EXTENSIONS.some((ext) => name.endsWith(ext));
  
  if (mime && !ALLOWED_MIME_TYPES.includes(mime) && !hasValidExt) {
    return "Invalid file format. Only JPG, PNG, WebP, or PDF documents are accepted.";
  }
  if (f.size > MAX_BYTES) {
    return `File is too large (${formatBytes(f.size)}). Maximum allowed size is 5 MB.`;
  }
  if (f.size < MIN_BYTES) {
    return "File appears empty or corrupted. Please choose a valid file.";
  }
  return null;
}

/** Validate ID document number format based on selected ID type */
function validateIdNumberFormat(type, value) {
  if (!value || !value.trim()) return null; // Optional field
  const val = value.trim();

  if (type === "aadhaar") {
    const digitsOnly = val.replace(/[\s-]/g, "");
    if (!/^\d{12}$/.test(digitsOnly)) {
      return "Aadhaar number must contain exactly 12 digits.";
    }
    if (/^(\d)\1{11}$/.test(digitsOnly)) {
      return "Aadhaar number cannot consist of repetitive single digits.";
    }
    return null;
  }

  if (type === "passport") {
    const clean = val.replace(/[\s-]/g, "").toUpperCase();
    if (!/^[A-Z0-9]{6,9}$/.test(clean)) {
      return "Passport number must be 6 to 9 alphanumeric characters (e.g. A1234567).";
    }
    return null;
  }

  if (val.length < 4 || val.length > 32) {
    return "ID number must be between 4 and 32 characters in length.";
  }
  if (!/^[a-zA-Z0-9\s\-/_.]+$/.test(val)) {
    return "ID number contains invalid special characters.";
  }

  return null;
}

/** Component for uploading and validating a document file */
function FileField({ label, file, onPick, onRemove, testId, hint, error, required = true }) {
  const inputRef = useRef(null);
  const [preview, setPreview] = useState(null);
  const [isDragOver, setIsDragOver] = useState(false);

  // Generate instant image preview URL
  useEffect(() => {
    if (file && file.type && file.type.startsWith("image/")) {
      const url = URL.createObjectURL(file);
      setPreview(url);
      return () => URL.revokeObjectURL(url);
    }
    setPreview(null);
    return undefined;
  }, [file]);

  const handleFileChange = (incoming) => {
    if (!incoming) return;
    const err = validateFileObject(incoming);
    if (err) {
      toast.error(err);
    }
    onPick(incoming);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileChange(e.dataTransfer.files[0]);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const isPdf = file?.type === "application/pdf" || file?.name?.toLowerCase().endsWith(".pdf");

  return (
    <div className="space-y-1.5" data-testid={`${testId}-container`}>
      <div className="flex items-center justify-between">
        <label className="text-xs font-medium text-ex-text flex items-center gap-1.5">
          {label}
          {required && <span className="text-rose-400 font-bold">*</span>}
        </label>
        {file && !error && (
          <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-400">
            <Check className="h-3 w-3" /> Valid Document ({formatBytes(file.size)})
          </span>
        )}
      </div>

      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={`relative flex items-center gap-3.5 p-3 rounded-ex-ctrl border transition-all ${
          error
            ? "border-rose-500/60 bg-rose-500/[0.04]"
            : file
            ? "border-emerald-500/40 bg-emerald-500/[0.03]"
            : isDragOver
            ? "border-purple-400 bg-purple-500/10 scale-[1.005]"
            : "border-white/10 bg-white/[0.03] hover:border-purple-400/50"
        }`}
      >
        {/* Preview Thumbnail */}
        <div className="relative grid h-14 w-14 shrink-0 place-items-center overflow-hidden rounded-xl border border-white/10 bg-black/40 shadow-inner">
          {preview ? (
            <img
              src={preview}
              alt="Document preview"
              className="h-full w-full object-cover"
              data-testid={`${testId}-preview`}
            />
          ) : isPdf ? (
            <FileText className="h-6 w-6 text-purple-300" />
          ) : file ? (
            <FileImage className="h-6 w-6 text-emerald-300" />
          ) : (
            <Camera className="h-6 w-6 text-ex-muted/60" />
          )}
        </div>

        {/* Info & Select Area */}
        <div className="flex-1 min-w-0">
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            data-testid={testId}
            className="w-full text-left focus:outline-none group"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="block truncate text-xs font-semibold text-ex-text group-hover:text-purple-300 transition">
                {file ? file.name : "Choose or drag ID document file"}
              </span>
              <span className="text-[11px] font-semibold text-purple-400 hover:text-purple-300 shrink-0">
                {file ? "Change" : "Browse"}
              </span>
            </div>
            <span className="block text-[11px] text-ex-muted truncate mt-0.5">
              {file ? `${file.type || "Document"} · ${formatBytes(file.size)}` : hint}
            </span>
          </button>
        </div>

        {/* Remove Button if file selected */}
        {file && onRemove && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onRemove();
            }}
            title="Remove document"
            className="p-1.5 rounded-lg text-ex-muted hover:text-rose-400 hover:bg-rose-500/10 transition shrink-0"
            data-testid={`${testId}-remove`}
          >
            <Trash2 className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Hidden Native File Input */}
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,application/pdf"
        className="hidden"
        onChange={(e) => {
          handleFileChange(e.target.files?.[0] || null);
          e.target.value = ""; // Reset so re-picking the same file triggers change
        }}
      />

      {/* Inline Field Error */}
      {error && (
        <div
          className="flex items-center gap-1.5 text-xs text-rose-400 font-medium pt-0.5"
          data-testid={`${testId}-error`}
        >
          <AlertCircle className="h-3.5 w-3.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}

const SELFIE_TIPS = [
  "Use clear, natural lighting — face the light source directly",
  "Position your face completely inside the camera oval frame",
  "Remove sunglasses, hats, or face coverings before taking photo",
  "Hold device steady at eye level for sharp facial focus",
];

function SelfieTips() {
  return (
    <div className="rounded-ex-ctrl border border-purple-500/20 bg-purple-500/[0.05] p-3.5" data-testid="kyc-selfie-tips">
      <div className="flex items-center gap-2 text-xs font-semibold text-purple-200">
        <Lightbulb className="h-4 w-4 text-purple-400 shrink-0" /> Requirements for Live Identity Selfie
      </div>
      <ul className="mt-2.5 grid grid-cols-1 sm:grid-cols-2 gap-2">
        {SELFIE_TIPS.map((t) => (
          <li key={t} className="flex items-start gap-2 text-[11px] text-ex-muted leading-relaxed">
            <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-purple-400" />
            <span>{t}</span>
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
      <div className="flex items-start gap-3.5 rounded-ex border border-emerald-500/30 bg-emerald-500/10 p-4" data-testid="kyc-status-approved">
        <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-400 mt-0.5" />
        <div>
          <div className="text-sm font-bold text-emerald-200">Identity Verification Approved</div>
          <div className="text-xs text-emerald-200/80 mt-0.5">
            Your KYC identity verification is verified and active. All account withdrawals and full platform features are unlocked.
          </div>
          {kyc.id_type && (
            <div className="mt-2 text-[11px] text-emerald-300 font-mono">
              Verified ID Type: {kyc.id_type.toUpperCase()} {kyc.id_number_masked ? `· ${kyc.id_number_masked}` : ""}
            </div>
          )}
        </div>
      </div>
    );
  }
  if (s === "pending") {
    return (
      <div className="flex items-start gap-3.5 rounded-ex border border-amber-500/30 bg-amber-500/10 p-4" data-testid="kyc-status-pending">
        <Clock className="h-5 w-5 shrink-0 text-amber-400 mt-0.5 animate-pulse" />
        <div>
          <div className="text-sm font-bold text-amber-200">Verification Under Admin Review</div>
          <div className="text-xs text-amber-200/80 mt-0.5">
            Your uploaded government ID documents and camera selfie have been received and are currently queued for manual compliance review.
          </div>
          <div className="mt-2 text-[11px] text-amber-300/80">
            Average review turnaround: Under 2 to 6 business hours.
          </div>
        </div>
      </div>
    );
  }
  if (s === "rejected") {
    return (
      <div className="flex items-start gap-3.5 rounded-ex border border-rose-500/30 bg-rose-500/10 p-4" data-testid="kyc-status-rejected">
        <XCircle className="h-5 w-5 shrink-0 text-rose-400 mt-0.5" />
        <div>
          <div className="text-sm font-bold text-rose-200">Verification Rejected — Resubmission Required</div>
          <div className="text-xs text-rose-200/90 mt-1">
            <strong>Reason provided:</strong> {kyc.reject_reason || "The submitted ID documents or selfie photo were unclear, expired, or failed verification."}
          </div>
          <p className="text-[11px] text-rose-300/70 mt-1">
            Please review the guidelines below, provide high-resolution images, and retake your camera selfie.
          </p>
        </div>
      </div>
    );
  }
  return null;
}

export default function KYCPage() {
  const { data: kyc, isLoading } = useKyc();
  const submitKyc = useSubmitKyc();

  // Form Field States
  const [idType, setIdType] = useState("aadhaar");
  const [idNumber, setIdNumber] = useState("");
  
  // Single document for non-Aadhaar IDs (National ID, Passport, Other)
  const [idDoc, setIdDoc] = useState(null);

  // Two separate documents specifically for Aadhaar
  const [idFrontDoc, setIdFrontDoc] = useState(null);
  const [idBackDoc, setIdBackDoc] = useState(null);

  // Live camera selfie blob (strictly camera-based)
  const [selfieBlob, setSelfieBlob] = useState(null);

  // Touched state to trigger error states cleanly
  const [hasAttemptedSubmit, setHasAttemptedSubmit] = useState(false);
  const [idNumberTouched, setIdNumberTouched] = useState(false);
  const [serverErrors, setServerErrors] = useState({});

  const selectedTypeConfig = useMemo(() => {
    return ID_TYPES.find((t) => t.value === idType) || ID_TYPES[0];
  }, [idType]);

  const isAadhaar = idType === "aadhaar";

  // Real-time Field Validations
  const idNumberError = useMemo(() => {
    return validateIdNumberFormat(idType, idNumber);
  }, [idType, idNumber]);

  const idDocError = useMemo(() => {
    if (isAadhaar) return null;
    if (!idDoc) {
      return hasAttemptedSubmit ? "Government ID document (Front) is required." : null;
    }
    return validateFileObject(idDoc);
  }, [isAadhaar, idDoc, hasAttemptedSubmit]);

  const idFrontError = useMemo(() => {
    if (!isAadhaar) return null;
    if (!idFrontDoc) {
      return hasAttemptedSubmit ? "Aadhaar Front Side document is required." : null;
    }
    return validateFileObject(idFrontDoc);
  }, [isAadhaar, idFrontDoc, hasAttemptedSubmit]);

  const idBackError = useMemo(() => {
    if (!isAadhaar) return null;
    if (!idBackDoc) {
      return hasAttemptedSubmit ? "Aadhaar Back Side document is required." : null;
    }
    return validateFileObject(idBackDoc);
  }, [isAadhaar, idBackDoc, hasAttemptedSubmit]);

  const selfieError = useMemo(() => {
    if (!selfieBlob) {
      return hasAttemptedSubmit ? "Live camera selfie is required to verify identity." : null;
    }
    return null;
  }, [selfieBlob, hasAttemptedSubmit]);

  // Overall validity check
  const hasValidDocs = isAadhaar
    ? Boolean(idFrontDoc && !validateFileObject(idFrontDoc) && idBackDoc && !validateFileObject(idBackDoc))
    : Boolean(idDoc && !validateFileObject(idDoc));

  const isFormValid = Boolean(
    idType &&
    hasValidDocs &&
    selfieBlob &&
    !idNumberError
  );

  // Handlers for File Selection
  const handlePickSingleId = (f) => {
    setServerErrors((prev) => ({ ...prev, id_document: undefined }));
    setIdDoc(f);
    if (f) {
      const err = validateFileObject(f);
      if (!err) {
        toast.success(`Selected ID document: ${f.name}`);
      }
    }
  };

  const handlePickFrontId = (f) => {
    setServerErrors((prev) => ({ ...prev, id_front_document: undefined }));
    setIdFrontDoc(f);
    if (f) {
      const err = validateFileObject(f);
      if (!err) {
        toast.success(`Selected Aadhaar Front: ${f.name}`);
      }
    }
  };

  const handlePickBackId = (f) => {
    setServerErrors((prev) => ({ ...prev, id_back_document: undefined }));
    setIdBackDoc(f);
    if (f) {
      const err = validateFileObject(f);
      if (!err) {
        toast.success(`Selected Aadhaar Back: ${f.name}`);
      }
    }
  };

  const handleCaptureComplete = (blob) => {
    setServerErrors((prev) => ({ ...prev, selfie: undefined }));
    setSelfieBlob(blob);
    toast.success("Live identity selfie captured and validated!");
  };

  const handleCameraReset = () => {
    setSelfieBlob(null);
    toast.info("Selfie photo cleared. Please take a new live photo.");
  };

  // Format helper for Aadhaar typing
  const handleIdNumberChange = (e) => {
    setServerErrors((prev) => ({ ...prev, id_number: undefined }));
    let val = e.target.value;
    if (idType === "aadhaar") {
      // Allow only numbers and spaces
      const cleanDigits = val.replace(/\D/g, "").slice(0, 12);
      // Group in 4s: XXXX XXXX XXXX
      const parts = cleanDigits.match(/.{1,4}/g) || [];
      val = parts.join(" ");
    } else if (idType === "passport") {
      val = val.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 9);
    }
    setIdNumber(val);
  };

  const submit = async (e) => {
    e.preventDefault();
    setHasAttemptedSubmit(true);
    setServerErrors({});

    // Client-side Validation Checks
    if (idNumberError) {
      toast.error(`Invalid ID Number: ${idNumberError}`);
      return;
    }

    if (isAadhaar) {
      if (!idFrontDoc) {
        toast.error("Please upload Aadhaar Front Side document.");
        return;
      }
      const frontErr = validateFileObject(idFrontDoc);
      if (frontErr) {
        toast.error(`Aadhaar Front Error: ${frontErr}`);
        return;
      }

      if (!idBackDoc) {
        toast.error("Please upload Aadhaar Back Side document.");
        return;
      }
      const backErr = validateFileObject(idBackDoc);
      if (backErr) {
        toast.error(`Aadhaar Back Error: ${backErr}`);
        return;
      }
    } else {
      if (!idDoc) {
        toast.error("Please upload your government ID document.");
        return;
      }
      const docErr = validateFileObject(idDoc);
      if (docErr) {
        toast.error(`Document Error: ${docErr}`);
        return;
      }
    }

    if (!selfieBlob) {
      toast.error("Please take a live selfie with your camera before submitting.");
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
      toast.success("KYC submitted successfully — pending manual admin review!");
      setIdNumber("");
      setIdDoc(null);
      setIdFrontDoc(null);
      setIdBackDoc(null);
      setSelfieBlob(null);
      setHasAttemptedSubmit(false);
    } catch (err) {
      const respData = err?.response?.data;
      if (respData?.field) {
        setServerErrors({ [respData.field]: respData.detail || respData.message });
      }
      toast.error(apiError(err, "Could not submit KYC verification"));
    }
  };

  const canSubmitForm = kyc && (kyc.status === "none" || kyc.status === "rejected");

  return (
    <div data-testid="kyc-page" className="pb-16">
      <PageHeading
        title="Identity Verification (KYC)"
        subtitle="Verify your identity with official government ID and live camera photo to unlock withdrawals."
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
              <div className="flex items-center justify-between border-b border-white/10 pb-3">
                <div>
                  <div className="text-sm font-semibold text-ex-text">
                    {kyc.status === "rejected" ? "Resubmit Identity Verification" : "Submit Identity Verification"}
                  </div>
                  <p className="mt-0.5 text-xs text-ex-muted">
                    Ensure all document photos are sharp, unaltered, and completely legible.
                  </p>
                </div>
                <span className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-purple-500/10 text-purple-300 text-[11px] font-medium border border-purple-500/20">
                  <CreditCard className="h-3 w-3" /> Tier 1 Verification
                </span>
              </div>

              {/* Requirement Checklist Badges */}
              <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px]">
                <div
                  className={`p-2 rounded-xl border flex items-center gap-2 transition ${
                    idType
                      ? "border-emerald-500/30 bg-emerald-500/5 text-emerald-300"
                      : "border-white/10 bg-white/[0.02] text-ex-muted"
                  }`}
                >
                  <FileCheck className="h-3.5 w-3.5 shrink-0" />
                  <span className="truncate">1. ID Type</span>
                </div>

                <div
                  className={`p-2 rounded-xl border flex items-center gap-2 transition ${
                    isAadhaar
                      ? idFrontDoc && !idFrontError
                        ? "border-emerald-500/30 bg-emerald-500/5 text-emerald-300"
                        : "border-white/10 bg-white/[0.02] text-ex-muted"
                      : idDoc && !idDocError
                      ? "border-emerald-500/30 bg-emerald-500/5 text-emerald-300"
                      : "border-white/10 bg-white/[0.02] text-ex-muted"
                  }`}
                >
                  <UploadCloud className="h-3.5 w-3.5 shrink-0" />
                  <span className="truncate">{isAadhaar ? "2. ID Front" : "2. ID Document"}</span>
                </div>

                <div
                  className={`p-2 rounded-xl border flex items-center gap-2 transition ${
                    isAadhaar
                      ? idBackDoc && !idBackError
                        ? "border-emerald-500/30 bg-emerald-500/5 text-emerald-300"
                        : "border-white/10 bg-white/[0.02] text-ex-muted"
                      : "border-emerald-500/30 bg-emerald-500/5 text-emerald-300"
                  }`}
                >
                  <UploadCloud className="h-3.5 w-3.5 shrink-0" />
                  <span className="truncate">{isAadhaar ? "3. ID Back" : "3. Back (N/A)"}</span>
                </div>

                <div
                  className={`p-2 rounded-xl border flex items-center gap-2 transition ${
                    selfieBlob
                      ? "border-emerald-500/30 bg-emerald-500/5 text-emerald-300"
                      : "border-white/10 bg-white/[0.02] text-ex-muted"
                  }`}
                >
                  <Camera className="h-3.5 w-3.5 shrink-0" />
                  <span className="truncate">4. Camera Selfie</span>
                </div>
              </div>

              <form onSubmit={submit} className="mt-5 space-y-4" data-testid="kyc-form" noValidate>
                {/* ID Type Selector */}
                <div>
                  <label className="text-xs font-medium text-ex-text flex items-center gap-1.5">
                    Government ID Document Type <span className="text-rose-400 font-bold">*</span>
                  </label>
                  <select
                    value={idType}
                    onChange={(e) => {
                      setIdType(e.target.value);
                      setIdNumber("");
                      setServerErrors({});
                    }}
                    data-testid="kyc-id-type"
                    className="mt-1.5 w-full rounded-ex-ctrl bg-white/5 border border-white/10 px-3.5 py-2.5 text-xs text-ex-text focus:border-purple-400 focus:outline-none transition shadow-inner"
                  >
                    {ID_TYPES.map((t) => (
                      <option key={t.value} value={t.value} className="bg-[#17161d] text-ex-text">
                        {t.label}
                      </option>
                    ))}
                  </select>
                  <p className="mt-1 text-[11px] text-purple-300/80">{selectedTypeConfig.helper}</p>
                </div>

                {/* ID Number Input with Realtime Validation */}
                <div>
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-medium text-ex-text flex items-center gap-1.5">
                      ID Document Number <span className="text-white/40 font-normal">(Optional, for faster verification)</span>
                    </label>
                    {idNumber && !idNumberError && (
                      <span className="inline-flex items-center gap-1 text-[11px] text-emerald-400 font-medium">
                        <Check className="h-3 w-3" /> Valid Format
                      </span>
                    )}
                  </div>
                  <div className="relative mt-1.5">
                    <input
                      type="text"
                      value={idNumber}
                      onChange={handleIdNumberChange}
                      onBlur={() => setIdNumberTouched(true)}
                      placeholder={selectedTypeConfig.placeholder}
                      data-testid="kyc-id-number"
                      className={`w-full rounded-ex-ctrl bg-white/5 border px-3.5 py-2.5 text-xs text-ex-text placeholder:text-ex-muted/50 focus:outline-none transition shadow-inner ${
                        (idNumberTouched || hasAttemptedSubmit) && idNumberError
                          ? "border-rose-500/60 focus:border-rose-500"
                          : idNumber && !idNumberError
                          ? "border-emerald-500/50 focus:border-emerald-500"
                          : "border-white/10 focus:border-purple-400"
                      }`}
                    />
                  </div>

                  {(idNumberTouched || hasAttemptedSubmit) && idNumberError && (
                    <div className="mt-1 flex items-center gap-1.5 text-xs text-rose-400 font-medium" data-testid="kyc-id-number-error">
                      <AlertCircle className="h-3.5 w-3.5 shrink-0" />
                      <span>{idNumberError}</span>
                    </div>
                  )}

                  {serverErrors.id_number && (
                    <div className="mt-1 flex items-center gap-1.5 text-xs text-rose-400 font-medium">
                      <AlertCircle className="h-3.5 w-3.5 shrink-0" />
                      <span>{serverErrors.id_number}</span>
                    </div>
                  )}

                  <p className="mt-1 text-[11px] text-ex-muted">
                    Stored with military-grade encryption — accessible solely to authorized compliance officers.
                  </p>
                </div>

                {/* Aadhaar Dual Upload vs Standard Single Upload */}
                {isAadhaar ? (
                  <div className="space-y-3.5 rounded-xl border border-white/5 bg-white/[0.01] p-3.5" data-testid="aadhaar-upload-section">
                    <div className="text-xs font-semibold text-ex-text flex items-center gap-2">
                      <FileCheck className="h-4 w-4 text-purple-400" /> Aadhaar Card Dual-Sided Verification
                    </div>
                    <FileField
                      label="Aadhaar Front Side (Showing Photo & Name)"
                      file={idFrontDoc}
                      onPick={handlePickFrontId}
                      onRemove={() => setIdFrontDoc(null)}
                      testId="kyc-id-front-upload"
                      hint="JPG, PNG, WebP or PDF · max 5 MB"
                      error={serverErrors.id_front_document || idFrontError}
                      required={true}
                    />

                    <FileField
                      label="Aadhaar Back Side (Showing Address & QR)"
                      file={idBackDoc}
                      onPick={handlePickBackId}
                      onRemove={() => setIdBackDoc(null)}
                      testId="kyc-id-back-upload"
                      hint="JPG, PNG, WebP or PDF · max 5 MB"
                      error={serverErrors.id_back_document || idBackError}
                      required={true}
                    />
                  </div>
                ) : (
                  <div className="space-y-3.5 rounded-xl border border-white/5 bg-white/[0.01] p-3.5">
                    <FileField
                      label={`${selectedTypeConfig.label} Document`}
                      file={idDoc}
                      onPick={handlePickSingleId}
                      onRemove={() => setIdDoc(null)}
                      testId="kyc-id-upload"
                      hint="JPG, PNG, WebP or PDF · max 5 MB"
                      error={serverErrors.id_document || idDocError}
                      required={true}
                    />
                  </div>
                )}

                {/* Guidelines Tips */}
                <SelfieTips />

                {/* Direct Camera-Only Selfie */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-medium text-ex-text flex items-center gap-1.5">
                      Live Camera Face Photo <span className="text-rose-400 font-bold">*</span>
                    </label>
                    {selfieBlob && (
                      <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-400">
                        <Check className="h-3 w-3" /> Live Selfie Captured
                      </span>
                    )}
                  </div>
                  <KycCameraCapture
                    onCaptureComplete={handleCaptureComplete}
                    onReset={handleCameraReset}
                    disabled={submitKyc.isPending}
                  />
                  {(serverErrors.selfie || selfieError) && (
                    <div className="mt-1 flex items-center gap-1.5 text-xs text-rose-400 font-medium" data-testid="kyc-selfie-error">
                      <AlertCircle className="h-3.5 w-3.5 shrink-0" />
                      <span>{serverErrors.selfie || selfieError}</span>
                    </div>
                  )}
                </div>

                {/* Form Summary Alert if Invalid on Submit Attempt */}
                {hasAttemptedSubmit && !isFormValid && (
                  <div className="p-3 rounded-xl border border-rose-500/30 bg-rose-500/10 text-xs text-rose-300 space-y-1 animate-in fade-in duration-200">
                    <div className="font-semibold flex items-center gap-1.5">
                      <AlertCircle className="h-4 w-4 shrink-0 text-rose-400" />
                      Please complete the following required items:
                    </div>
                    <ul className="list-disc list-inside space-y-0.5 text-[11px] text-rose-200/90 pl-1">
                      {isAadhaar && !idFrontDoc && <li>Upload Aadhaar Front Side document</li>}
                      {isAadhaar && !idBackDoc && <li>Upload Aadhaar Back Side document</li>}
                      {!isAadhaar && !idDoc && <li>Upload your official Government ID document</li>}
                      {!selfieBlob && <li>Take a live camera selfie to verify your face</li>}
                      {idNumberError && <li>Fix ID document number format</li>}
                    </ul>
                  </div>
                )}

                {/* Submit Action */}
                <EasyXButton
                  type="submit"
                  className="w-full py-3"
                  disabled={submitKyc.isPending}
                  loading={submitKyc.isPending}
                  data-testid="kyc-submit"
                >
                  {kyc.status === "rejected" ? "Resubmit for Manual Review" : "Submit for Manual Review"}
                </EasyXButton>
              </form>
            </EasyXCard>
          ) : (
            <EasyXCard>
              <div className="flex items-center gap-3">
                <ShieldCheck className="h-6 w-6 text-emerald-400" />
                <div>
                  <div className="text-sm font-semibold text-ex-text">
                    {kyc.status === "pending" ? "Verification In Progress" : "Identity Verified"}
                  </div>
                  <p className="text-xs text-ex-muted mt-0.5">
                    {kyc.status === "pending"
                      ? "Your submitted documents and live selfie are currently under manual review by compliance admins. You will receive an alert once approved."
                      : "Your identity has been successfully verified. You now have unrestricted access to fund withdrawals and platform services."}
                  </p>
                </div>
              </div>
            </EasyXCard>
          )}
        </div>
      )}
    </div>
  );
}
