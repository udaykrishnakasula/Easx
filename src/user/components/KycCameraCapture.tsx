import React, { useEffect, useRef, useState } from "react";
import {
  Camera,
  CheckCircle2,
  AlertCircle,
  RotateCcw,
  RefreshCw,
  Video,
  Info,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";
import { EasyXButton } from "@/design/EasyX";

export type KycCameraStatus =
  | "IDLE"
  | "INITIALIZING"
  | "CAMERA_ACTIVE"
  | "CAPTURED"
  | "PERMISSION_DENIED"
  | "CAMERA_UNAVAILABLE"
  | "BROWSER_UNSUPPORTED"
  | "CAMERA_ERROR";

export type CameraFacingMode = "user" | "environment";

interface KycCameraCaptureProps {
  onCaptureComplete: (blob: Blob | File, previewUrl: string) => void;
  onReset: () => void;
  disabled?: boolean;
}

const SUPPORTED_MIME_TYPES = ["image/jpeg", "image/jpg", "image/png", "image/webp"];
const MAX_FILE_SIZE_MB = 10;

/**
 * Resizes and converts an image file to a clean base64 data URL and Blob
 * Reused from the proven Deposit payment proof processor
 */
const processImageFile = (file: File): Promise<{ dataUrl: string; blob: Blob }> => {
  return new Promise((resolve, reject) => {
    if (!SUPPORTED_MIME_TYPES.includes(file.type.toLowerCase())) {
      reject(new Error("Supported formats are JPG, PNG, and WEBP only."));
      return;
    }
    if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
      reject(new Error(`File size must be under ${MAX_FILE_SIZE_MB}MB.`));
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const result = e.target?.result;
      if (!result) {
        reject(new Error("Failed to read image file."));
        return;
      }

      const img = new Image();
      img.onload = () => {
        const maxDimension = 1800;
        let width = img.width;
        let height = img.height;

        if (width > maxDimension || height > maxDimension) {
          if (width > height) {
            height = Math.round((height * maxDimension) / width);
            width = maxDimension;
          } else {
            width = Math.round((width * maxDimension) / height);
            height = maxDimension;
          }
        }

        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext("2d");
        if (!ctx) {
          fetch(String(result))
            .then((r) => r.blob())
            .then((blob) => resolve({ dataUrl: String(result), blob }))
            .catch(() => resolve({ dataUrl: String(result), blob: file }));
          return;
        }
        ctx.drawImage(img, 0, 0, width, height);
        const dataUrl = canvas.toDataURL("image/jpeg", 0.92);
        canvas.toBlob(
          (blob) => {
            resolve({ dataUrl, blob: blob || file });
          },
          "image/jpeg",
          0.92
        );
      };
      img.onerror = () => {
        fetch(String(result))
          .then((r) => r.blob())
          .then((blob) => resolve({ dataUrl: String(result), blob }))
          .catch(() => resolve({ dataUrl: String(result), blob: file }));
      };
      img.src = String(result);
    };
    reader.onerror = () => reject(new Error("Error reading file."));
    reader.readAsDataURL(file);
  });
};

function classifyCameraError(err: any): {
  status: KycCameraStatus;
  message: string;
} {
  const name = err?.name || "";
  const msg = String(err?.message || "").toLowerCase();

  // 1. Permission Denied / Blocked
  if (
    name === "NotAllowedError" ||
    name === "PermissionDeniedError" ||
    name === "SecurityError" ||
    msg.includes("permission denied") ||
    msg.includes("permission dismissed") ||
    msg.includes("not allowed")
  ) {
    return {
      status: "PERMISSION_DENIED",
      message:
        "Camera access is blocked or was previously denied. Please enable camera permission in your browser URL bar / site settings and try again.",
    };
  }

  // 2. Hardware Missing / Not Found
  if (
    name === "NotFoundError" ||
    name === "DevicesNotFoundError" ||
    msg.includes("not found") ||
    msg.includes("no camera") ||
    msg.includes("requested device not found")
  ) {
    return {
      status: "CAMERA_UNAVAILABLE",
      message:
        "No camera detected on this device. Please connect a webcam or open EasyX on a smartphone with a camera.",
    };
  }

  // 3. Camera Busy / Locked by another app
  if (
    name === "NotReadableError" ||
    name === "TrackStartError" ||
    msg.includes("in use") ||
    msg.includes("could not start video source") ||
    msg.includes("device in use") ||
    msg.includes("hardware error")
  ) {
    return {
      status: "CAMERA_UNAVAILABLE",
      message:
        "Your camera is currently in use by another application or browser tab. Please close other camera apps and try again.",
    };
  }

  // 4. Unsupported Browser / Insecure Context
  if (
    name === "BrowserNotSupportedError" ||
    name === "InsecureContextError" ||
    msg.includes("not supported") ||
    msg.includes("https")
  ) {
    return {
      status: "BROWSER_UNSUPPORTED",
      message:
        "Direct camera access is not supported on this browser or requires a secure HTTPS connection. Please open EasyX in Google Chrome, Safari, or Microsoft Edge.",
    };
  }

  // 5. Fallback generic error
  return {
    status: "CAMERA_ERROR",
    message: err?.message || "Failed to start camera. Please check your browser settings and try again.",
  };
}

/**
 * Intelligent MediaStream retriever with tiered device constraints
 * Specifically optimizes for front-facing 'user' selfie mode or rear 'environment' mode on mobile.
 */
const getCameraStream = async (targetFacingMode: CameraFacingMode = "user"): Promise<MediaStream> => {
  const mediaDevices = typeof navigator !== "undefined" ? navigator.mediaDevices : null;

  if (!mediaDevices || typeof mediaDevices.getUserMedia !== "function") {
    // Check legacy getUserMedia for older mobile webviews
    const legacyGetUserMedia =
      typeof navigator !== "undefined"
        ? (navigator as any).webkitGetUserMedia ||
          (navigator as any).mozGetUserMedia ||
          (navigator as any).getUserMedia
        : null;

    if (!legacyGetUserMedia) {
      const err: any = new Error("Camera API is not supported on this browser.");
      err.name = "BrowserNotSupportedError";
      throw err;
    }

    return new Promise<MediaStream>((resolve, reject) => {
      legacyGetUserMedia.call(navigator, { video: true, audio: false }, resolve, reject);
    });
  }

  // Tier 1: Optimal standard resolution with ideal facingMode
  try {
    return await mediaDevices.getUserMedia({
      video: {
        facingMode: targetFacingMode ? { ideal: targetFacingMode } : "user",
        width: { ideal: 1280 },
        height: { ideal: 720 },
      },
      audio: false,
    });
  } catch (err1: any) {
    if (
      err1.name === "NotAllowedError" ||
      err1.name === "PermissionDeniedError" ||
      err1.name === "SecurityError"
    ) {
      throw err1;
    }

    // Tier 2: Plain facingMode
    try {
      return await mediaDevices.getUserMedia({
        video: {
          facingMode: targetFacingMode || "user",
        },
        audio: false,
      });
    } catch (err2: any) {
      if (
        err2.name === "NotAllowedError" ||
        err2.name === "PermissionDeniedError" ||
        err2.name === "SecurityError"
      ) {
        throw err2;
      }

      // Tier 3: Basic unconstrained video
      return await mediaDevices.getUserMedia({
        video: true,
        audio: false,
      });
    }
  }
};

export default function KycCameraCapture({
  onCaptureComplete,
  onReset,
  disabled = false,
}: KycCameraCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  const [status, setStatus] = useState<KycCameraStatus>("IDLE");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [capturedPreview, setCapturedPreview] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [facingMode, setFacingMode] = useState<CameraFacingMode>("user");
  const [hasMultipleCameras, setHasMultipleCameras] = useState(false);

  // Check for multi-camera support (e.g. front and back cameras on smartphones)
  useEffect(() => {
    if (typeof navigator !== "undefined" && navigator.mediaDevices?.enumerateDevices) {
      navigator.mediaDevices
        .enumerateDevices()
        .then((devices) => {
          const videoInputs = devices.filter((d) => d.kind === "videoinput");
          if (videoInputs.length > 1) {
            setHasMultipleCameras(true);
          }
        })
        .catch(() => {
          // ignore device enumeration errors
        });
    }
  }, []);

  // Stop camera stream tracks and clear video source
  const stopCameraStream = () => {
    if (streamRef.current) {
      try {
        const tracks = streamRef.current.getTracks();
        tracks.forEach((track) => {
          try {
            track.stop();
          } catch {
            // ignore track stop error
          }
        });
      } catch {
        // ignore
      }
      streamRef.current = null;
    }
    if (videoRef.current) {
      try {
        videoRef.current.srcObject = null;
      } catch {
        // ignore
      }
    }
  };

  // Clean up camera stream and object URLs on unmount
  useEffect(() => {
    return () => {
      stopCameraStream();
      if (capturedPreview && capturedPreview.startsWith("blob:")) {
        URL.revokeObjectURL(capturedPreview);
      }
    };
  }, [capturedPreview]);

  // Request camera from browser and start live stream immediately
  const startCameraStream = async (targetMode: CameraFacingMode = facingMode) => {
    try {
      setErrorMessage(null);
      setStatus("INITIALIZING");
      stopCameraStream();

      const stream = await getCameraStream(targetMode);

      streamRef.current = stream;
      setFacingMode(targetMode);
      setStatus("CAMERA_ACTIVE");

      // Attach stream to video element with mobile compatibility attributes
      setTimeout(() => {
        if (videoRef.current) {
          const video = videoRef.current;
          video.srcObject = stream;
          video.setAttribute("playsinline", "true");
          video.setAttribute("webkit-playsinline", "true");
          video.muted = true;
          video.autoplay = true;

          const playPromise = video.play();
          if (playPromise !== undefined) {
            playPromise.catch((err) => {
              console.warn("Autoplay promise notice:", err);
              video.onloadedmetadata = () => {
                video.play().catch((e) => console.warn("Retry play error:", e));
              };
            });
          }
        }
      }, 60);
    } catch (err: any) {
      console.warn("Camera access error:", err);
      stopCameraStream();
      const classified = classifyCameraError(err);
      setStatus(classified.status);
      setErrorMessage(classified.message);
    }
  };

  // User taps "Open Camera & Take Photo" - launches device native camera directly like Deposit Proof
  const handleOpenClick = () => {
    if (disabled) return;
    setErrorMessage(null);
    if (cameraInputRef.current) {
      cameraInputRef.current.click();
    } else {
      startCameraStream(facingMode);
    }
  };

  // Direct device camera capture fallback (e.g. mobile direct camera)
  const handleDeviceCameraCapture = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      setIsProcessing(true);
      const { dataUrl, blob } = await processImageFile(file);
      setCapturedPreview(dataUrl);
      stopCameraStream();
      setStatus("CAPTURED");
      const fileObj = blob instanceof File ? blob : new File([blob], "live_selfie.jpg", { type: "image/jpeg" });
      onCaptureComplete(fileObj, dataUrl);
      toast.success("Camera photo uploaded successfully!");
    } catch (err: any) {
      const msg = err.message || "Failed to process photo from camera.";
      setErrorMessage(msg);
      setStatus("CAMERA_ERROR");
      toast.error(`Photo upload failed: ${msg}`);
    } finally {
      setIsProcessing(false);
      if (cameraInputRef.current) cameraInputRef.current.value = "";
    }
  };

  // Toggle between Front ('user') and Rear ('environment') cameras
  const handleToggleFacingMode = async () => {
    const nextMode: CameraFacingMode = facingMode === "user" ? "environment" : "user";
    await startCameraStream(nextMode);
  };

  // Capture frame from live video
  const handleCapturePhoto = async () => {
    if (!videoRef.current) return;

    try {
      setIsProcessing(true);
      const video = videoRef.current;
      const width = video.videoWidth || video.clientWidth || 640;
      const height = video.videoHeight || video.clientHeight || 480;

      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext("2d");
      if (!ctx) throw new Error("Could not get 2d context for canvas capture.");

      // Mirror horizontally ONLY for front-facing 'user' mode for natural selfie perspective
      if (facingMode === "user") {
        ctx.translate(width, 0);
        ctx.scale(-1, 1);
      }

      ctx.drawImage(video, 0, 0, width, height);

      canvas.toBlob(
        (blob) => {
          setIsProcessing(false);
          if (!blob) {
            setErrorMessage("Failed to encode camera snapshot.");
            setStatus("CAMERA_ERROR");
            toast.error("Failed to process captured camera snapshot.");
            return;
          }

          const previewUrl = URL.createObjectURL(blob);
          setCapturedPreview(previewUrl);

          // Stop all camera tracks immediately after selfie capture
          stopCameraStream();
          setStatus("CAPTURED");

          // Notify parent component with clean Blob
          const file = new File([blob], "live_selfie.jpg", { type: "image/jpeg" });
          onCaptureComplete(file, previewUrl);
          toast.success("Live identity selfie captured successfully!");
        },
        "image/jpeg",
        0.95
      );
    } catch (err: any) {
      setIsProcessing(false);
      console.warn("Capture photo error:", err?.message || err);
      const msg = err.message || "Could not capture camera frame.";
      setErrorMessage(msg);
      setStatus("CAMERA_ERROR");
      toast.error(`Capture failed: ${msg}`);
    }
  };

  // Retake / reset camera
  const handleRetake = () => {
    stopCameraStream();
    if (capturedPreview && capturedPreview.startsWith("blob:")) {
      URL.revokeObjectURL(capturedPreview);
    }
    setCapturedPreview(null);
    setStatus("IDLE");
    setErrorMessage(null);
    onReset();
  };

  return (
    <div className="space-y-3" data-testid="kyc-camera-capture-container">
      {/* Hidden native camera capture fallback input for mobile/device direct capture */}
      <input
        type="file"
        ref={cameraInputRef}
        onChange={handleDeviceCameraCapture}
        accept="image/jpeg,image/png,image/webp"
        capture="user"
        className="hidden"
        data-testid="kyc-native-camera-input"
      />

      <div className="flex items-center justify-between">
        <label className="text-xs font-semibold text-ex-text flex items-center gap-1.5">
          <Camera className="h-4 w-4 text-ex-lav-300" />
          Live Selfie Photo <span className="text-white/40">(Camera only)</span>
        </label>

        {status === "CAMERA_ACTIVE" && (
          <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-400">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            {facingMode === "user" ? "Front Camera (Selfie)" : "Rear Camera"}
          </span>
        )}
      </div>

      {/* State 1: IDLE - Camera permission not yet requested */}
      {status === "IDLE" && (
        <div
          className="rounded-ex border border-dashed border-white/15 bg-white/[0.02] p-5 text-center transition hover:border-ex-accent/50"
          data-testid="kyc-camera-idle"
        >
          <div className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-ex-lav-400/15 text-ex-lav-300 mb-3">
            <Video className="h-6 w-6" />
          </div>
          <h4 className="text-sm font-semibold text-ex-text">Live Camera Photo Required</h4>
          <p className="mt-1 text-xs text-ex-muted max-w-md mx-auto">
            Take a real-time live selfie photo using your device camera. Photos are manually reviewed by our compliance team.
          </p>

          <div className="mt-4 flex flex-wrap items-center justify-center gap-2.5">
            <EasyXButton
              type="button"
              variant="accent"
              onClick={handleOpenClick}
              disabled={disabled}
              data-testid="btn-open-camera"
              className="px-6 py-2.5 text-xs font-bold shadow-lg shadow-purple-950/40"
            >
              <Camera className="mr-2 h-4 w-4" /> Open Camera &amp; Take Photo
            </EasyXButton>
          </div>
        </div>
      )}

      {/* State 2: INITIALIZING - Requesting browser camera permission */}
      {status === "INITIALIZING" && (
        <div
          className="rounded-ex border border-white/10 bg-white/[0.03] p-8 text-center"
          data-testid="kyc-camera-initializing"
        >
          <div className="h-7 w-7 border-2 border-ex-accent border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <div className="text-sm font-semibold text-ex-text">
            Connecting to {facingMode === "user" ? "Front" : "Rear"} Camera...
          </div>
          <p className="text-xs text-ex-muted mt-1">
            Please click <strong>&ldquo;Allow&rdquo;</strong> on the browser camera permission prompt.
          </p>
        </div>
      )}

      {/* State 3: CAMERA ACTIVE - Permission granted, live front-facing stream active */}
      {status === "CAMERA_ACTIVE" && (
        <div
          className="rounded-ex overflow-hidden border border-white/15 bg-black/70 relative"
          data-testid="kyc-camera-stream-active"
        >
          {/* Video Container with Oval Face Alignment Guide */}
          <div className="relative aspect-[4/3] w-full max-w-md mx-auto overflow-hidden bg-black flex items-center justify-center">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className={`h-full w-full object-cover ${facingMode === "user" ? "scale-x-[-1]" : ""}`}
              data-testid="kyc-live-video"
            />

            {/* Oval Guide Overlay */}
            <div className="absolute inset-0 pointer-events-none flex flex-col items-center justify-center">
              <div className="w-48 h-60 sm:w-56 sm:h-72 rounded-[50%] border-2 border-white/70 shadow-[0_0_0_9999px_rgba(0,0,0,0.55)]" />
              <div className="mt-3 px-3 py-1 rounded-full bg-black/80 backdrop-blur-sm text-[11px] font-medium text-white/90 border border-white/10">
                Center your face in the oval
              </div>
            </div>

            {/* Flip / Switch Camera Button overlay (when multiple cameras or mobile available) */}
            <button
              type="button"
              onClick={handleToggleFacingMode}
              className="absolute top-3 right-3 z-10 p-2 rounded-full bg-black/60 hover:bg-black/80 backdrop-blur-md text-white border border-white/20 transition flex items-center gap-1 text-[11px] font-medium shadow-lg"
              title={`Switch to ${facingMode === "user" ? "Rear" : "Front"} Camera`}
              data-testid="btn-switch-camera"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">{facingMode === "user" ? "Rear Camera" : "Front Camera"}</span>
            </button>
          </div>

          {/* Action Bar */}
          <div className="p-4 bg-ex-card border-t border-white/10 flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="text-xs text-ex-muted flex items-center gap-1.5">
              <Info className="h-3.5 w-3.5 text-ex-lav-300 shrink-0" />
              Look directly at the camera with clear lighting
            </div>

            <div className="flex items-center gap-2 w-full sm:w-auto">
              <EasyXButton
                type="button"
                variant="accent"
                onClick={handleCapturePhoto}
                loading={isProcessing}
                data-testid="btn-take-snapshot"
                className="flex-1 sm:flex-none text-xs font-bold px-6"
              >
                <Camera className="mr-1.5 h-4 w-4" /> Capture Photo
              </EasyXButton>

              <button
                type="button"
                onClick={handleRetake}
                className="p-2 rounded-ex-ctrl text-ex-muted hover:text-white hover:bg-white/5 transition"
                title="Cancel camera"
                data-testid="btn-close-camera"
              >
                <RotateCcw className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* State 4: CAPTURED - Live selfie photo captured */}
      {status === "CAPTURED" && capturedPreview && (
        <div
          className="rounded-ex border border-emerald-500/30 bg-emerald-500/10 p-4 transition-all"
          data-testid="kyc-photo-captured"
        >
          <div className="flex items-center gap-3.5">
            <div className="h-16 w-16 shrink-0 rounded-ex overflow-hidden border border-emerald-500/40 relative">
              <img
                src={capturedPreview}
                alt="Captured live selfie"
                className="h-full w-full object-cover"
                data-testid="kyc-captured-selfie-preview"
              />
              <div className="absolute bottom-0 right-0 bg-emerald-500 text-black p-0.5 rounded-tl">
                <CheckCircle2 className="h-3 w-3" />
              </div>
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <h4 className="text-sm font-bold text-emerald-200">Live Selfie Captured</h4>
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                  READY FOR SUBMISSION
                </span>
              </div>
              <p className="mt-0.5 text-xs text-emerald-200/80">
                Photo captured directly from device camera ({facingMode === "user" ? "Front Selfie" : "Rear Camera"}).
              </p>
            </div>

            <button
              type="button"
              onClick={handleRetake}
              data-testid="btn-retake-photo"
              className="text-xs text-emerald-300/90 hover:text-emerald-100 underline decoration-dotted ml-auto shrink-0 font-medium"
            >
              Retake
            </button>
          </div>
        </div>
      )}

      {/* State 5: PERMISSION DENIED - Blocked camera permission state */}
      {status === "PERMISSION_DENIED" && (
        <div
          className="rounded-ex border border-amber-500/30 bg-amber-500/10 p-4 space-y-3"
          data-testid="kyc-camera-blocked-banner"
        >
          <div className="flex items-start gap-3">
            <ShieldAlert className="h-5 w-5 text-amber-300 shrink-0 mt-0.5" />
            <div className="flex-1 space-y-2">
              <h4 className="text-sm font-semibold text-amber-200">
                Camera Access is Blocked
              </h4>
              <p className="text-xs text-amber-200/90 leading-relaxed">
                {errorMessage ||
                  "Camera access is blocked or was previously denied. Please enable camera permission in your browser URL bar / site settings and try again."}
              </p>

              {/* Step by step fix instructions */}
              <div className="rounded bg-black/30 p-2.5 text-[11px] text-amber-200/80 space-y-1.5 border border-amber-500/20">
                <div className="font-semibold text-amber-100">How to enable camera permissions:</div>
                <ol className="list-decimal list-inside space-y-1 text-white/80">
                  <li>Click the <strong>Lock / Settings icon (🔒 or 🎛️)</strong> on the left side of your browser address bar.</li>
                  <li>Set <strong>Camera</strong> permission to <strong>&ldquo;Allow&rdquo;</strong> (or Reset permissions).</li>
                  <li>Click <strong>&ldquo;Try Again&rdquo;</strong> below or refresh the page.</li>
                </ol>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-end gap-2 pt-2 border-t border-amber-500/20">
            <button
              type="button"
              onClick={() => cameraInputRef.current?.click()}
              className="text-xs text-white/70 hover:text-white underline mr-auto"
              data-testid="btn-open-device-camera-fallback"
            >
              Open Device Camera Directly
            </button>
            <EasyXButton
              type="button"
              variant="accent"
              onClick={() => startCameraStream(facingMode)}
              data-testid="btn-retry-open-camera"
              className="text-xs font-semibold h-8 px-4"
            >
              <RotateCcw className="mr-1.5 h-3.5 w-3.5" /> Try Again
            </EasyXButton>
          </div>
        </div>
      )}

      {/* State 6: CAMERA UNAVAILABLE - Hardware missing or locked by other app */}
      {status === "CAMERA_UNAVAILABLE" && (
        <div
          className="rounded-ex border border-amber-500/30 bg-amber-500/10 p-4 space-y-3"
          data-testid="kyc-camera-unavailable-banner"
        >
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-amber-300 shrink-0 mt-0.5" />
            <div className="flex-1 space-y-1.5">
              <h4 className="text-sm font-semibold text-amber-200">Camera Unavailable</h4>
              <p className="text-xs text-amber-200/90 leading-relaxed">
                {errorMessage ||
                  "No camera detected or the camera is in use by another application. Please check your camera hardware and try again."}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-end gap-2 pt-2 border-t border-amber-500/20">
            <button
              type="button"
              onClick={() => cameraInputRef.current?.click()}
              className="text-xs text-white/70 hover:text-white underline mr-auto"
              data-testid="btn-open-device-camera-fallback"
            >
              Open Device Camera Directly
            </button>
            <EasyXButton
              type="button"
              variant="accent"
              onClick={() => startCameraStream(facingMode)}
              data-testid="btn-retry-open-camera"
              className="text-xs font-semibold h-8 px-4"
            >
              <RotateCcw className="mr-1.5 h-3.5 w-3.5" /> Try Again
            </EasyXButton>
          </div>
        </div>
      )}

      {/* State 7: BROWSER UNSUPPORTED / GENERIC ERROR */}
      {(status === "BROWSER_UNSUPPORTED" || status === "CAMERA_ERROR") && (
        <div
          className="rounded-ex border border-amber-500/30 bg-amber-500/10 p-4 space-y-3"
          data-testid="kyc-camera-error-banner"
        >
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-amber-300 shrink-0 mt-0.5" />
            <div className="flex-1 space-y-1.5">
              <h4 className="text-sm font-semibold text-amber-200">
                {status === "BROWSER_UNSUPPORTED" ? "Browser Not Supported" : "Camera Access Issue"}
              </h4>
              <p className="text-xs text-amber-200/90 leading-relaxed">
                {errorMessage || "Unable to access camera on this browser."}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-end gap-2 pt-2 border-t border-amber-500/20">
            <button
              type="button"
              onClick={() => cameraInputRef.current?.click()}
              className="text-xs text-white/70 hover:text-white underline mr-auto"
              data-testid="btn-open-device-camera-fallback"
            >
              Open Device Camera Directly
            </button>
            <EasyXButton
              type="button"
              variant="accent"
              onClick={() => startCameraStream(facingMode)}
              data-testid="btn-retry-open-camera"
              className="text-xs font-semibold h-8 px-4"
            >
              <RotateCcw className="mr-1.5 h-3.5 w-3.5" /> Try Again
            </EasyXButton>
          </div>
        </div>
      )}
    </div>
  );
}


