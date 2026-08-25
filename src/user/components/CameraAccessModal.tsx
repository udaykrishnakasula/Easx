import React from "react";
import { Camera, ShieldCheck, Lock, X } from "lucide-react";
import { EasyXButton } from "@/design/EasyX";

export interface CameraAccessModalProps {
  isOpen: boolean;
  onAllow: () => void;
  onDeny: () => void;
  title?: string;
  description?: string;
  allowButtonText?: string;
  denyButtonText?: string;
}

/**
 * Reusable Camera Access Consent Modal
 *
 * Displays an explicit user-consent modal prior to requesting browser camera hardware
 * via `navigator.mediaDevices.getUserMedia()`.
 */
export default function CameraAccessModal({
  isOpen,
  onAllow,
  onDeny,
  title = "Camera Access Required",
  description = "EasyX needs access to your device camera to capture your live selfie for KYC verification. Your camera will only be accessed when you choose to take your selfie.",
  allowButtonText = "Allow Camera on This Site",
  denyButtonText = "Never Allow",
}: CameraAccessModalProps) {
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-200"
      role="dialog"
      aria-modal="true"
      aria-labelledby="camera-consent-title"
      data-testid="camera-consent-modal"
    >
      <div className="relative w-full max-w-md rounded-2xl border border-white/15 bg-[#121118] p-6 shadow-2xl space-y-5 text-center">
        {/* Close button */}
        <button
          type="button"
          onClick={onDeny}
          className="absolute right-4 top-4 rounded-full p-1.5 text-white/40 hover:text-white hover:bg-white/10 transition"
          aria-label="Close"
          data-testid="btn-close-consent-modal"
        >
          <X className="h-4 w-4" />
        </button>

        {/* Icon Header */}
        <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-gradient-to-b from-purple-500/20 to-purple-500/5 border border-purple-500/30 text-purple-300 shadow-inner">
          <Camera className="h-7 w-7" />
        </div>

        {/* Title & Description */}
        <div className="space-y-2">
          <h3
            id="camera-consent-title"
            className="text-lg font-bold text-white tracking-tight"
            data-testid="camera-consent-title"
          >
            {title}
          </h3>
          <p
            className="text-xs text-white/70 leading-relaxed px-2"
            data-testid="camera-consent-description"
          >
            {description}
          </p>
        </div>

        {/* Privacy & Security Assurances */}
        <div className="rounded-xl bg-white/[0.03] border border-white/10 p-3 text-left space-y-2 text-[11px] text-white/80">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-emerald-400 shrink-0" />
            <span>Live selfie verification only</span>
          </div>
          <div className="flex items-center gap-2">
            <Lock className="h-4 w-4 text-purple-400 shrink-0" />
            <span>No background recording or gallery uploads</span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col gap-2 pt-1">
          <EasyXButton
            type="button"
            variant="accent"
            onClick={onAllow}
            data-testid="btn-allow-camera-consent"
            className="w-full h-11 text-xs font-bold shadow-lg shadow-purple-950/40"
          >
            {allowButtonText}
          </EasyXButton>

          <button
            type="button"
            onClick={onDeny}
            data-testid="btn-deny-camera-consent"
            className="w-full py-2 text-xs font-medium text-white/50 hover:text-white hover:bg-white/5 rounded-xl transition"
          >
            {denyButtonText}
          </button>
        </div>
      </div>
    </div>
  );
}
