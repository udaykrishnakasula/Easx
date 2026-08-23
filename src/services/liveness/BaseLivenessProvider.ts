import {
  LivenessProvider,
  LivenessSessionInitParams,
  LivenessSessionResponse,
  LivenessVerificationResult,
} from "./types";
import { api } from "@/shared/lib/api";

/**
 * Base Abstract Adapter for Liveness Providers.
 * Handles common hardware camera lifecycle (front-facing stream, track teardown, frame capture).
 */
export abstract class BaseLivenessProvider implements LivenessProvider {
  abstract readonly name: string;
  abstract readonly isTestMode: boolean;

  protected activeStream: MediaStream | null = null;
  protected activeVideoElement: HTMLVideoElement | null = null;

  async initialize(): Promise<void> {
    // Default hook for provider SDK configuration
    return Promise.resolve();
  }

  async startSession(params: LivenessSessionInitParams): Promise<LivenessSessionResponse> {
    const res = await api.post("/kyc/liveness/session", params);
    return res.data;
  }

  async startCamera(
    videoElement: HTMLVideoElement,
    facingMode: "user" | "environment" = "user"
  ): Promise<MediaStream> {
    this.stopCamera();

    if (!navigator?.mediaDevices?.getUserMedia) {
      const err = new Error("Camera API is not supported on this browser/device.");
      (err as any).code = "CAMERA_UNAVAILABLE";
      throw err;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: facingMode },
          width: { ideal: 1280, max: 1920 },
          height: { ideal: 720, max: 1080 },
        },
        audio: false,
      });

      this.activeStream = stream;
      this.activeVideoElement = videoElement;

      videoElement.srcObject = stream;
      videoElement.setAttribute("playsinline", "true");
      videoElement.setAttribute("webkit-playsinline", "true");
      videoElement.muted = true;

      await videoElement.play();
      return stream;
    } catch (err: any) {
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        const error = new Error("Camera permission was denied. Please allow camera access in browser settings.");
        (error as any).code = "CAMERA_PERMISSION_DENIED";
        throw error;
      }
      if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
        const error = new Error("No front-facing camera found on this device.");
        (error as any).code = "CAMERA_UNAVAILABLE";
        throw error;
      }
      if (err.name === "NotReadableError" || err.name === "TrackStartError") {
        const error = new Error("Camera is already in use by another application.");
        (error as any).code = "CAMERA_UNAVAILABLE";
        throw error;
      }
      throw err;
    }
  }

  stopCamera(): void {
    if (this.activeStream) {
      this.activeStream.getTracks().forEach((track) => {
        try {
          track.stop();
        } catch {
          // ignore
        }
      });
      this.activeStream = null;
    }

    if (this.activeVideoElement) {
      try {
        this.activeVideoElement.srcObject = null;
      } catch {
        // ignore
      }
      this.activeVideoElement = null;
    }
  }

  /**
   * Helper: Grab a clean, cropped still JPEG frame directly from the running video element.
   */
  protected captureFrameAsBlob(video: HTMLVideoElement): Promise<Blob> {
    return new Promise((resolve, reject) => {
      try {
        const canvas = document.createElement("canvas");
        const w = video.videoWidth || 640;
        const h = video.videoHeight || 480;
        canvas.width = w;
        canvas.height = h;

        const ctx = canvas.getContext("2d");
        if (!ctx) {
          reject(new Error("Unable to create canvas context"));
          return;
        }

        // Draw image directly
        ctx.drawImage(video, 0, 0, w, h);
        canvas.toBlob(
          (blob) => {
            if (blob) resolve(blob);
            else reject(new Error("Failed to capture frame as image blob"));
          },
          "image/jpeg",
          0.92
        );
      } catch (err) {
        reject(err);
      }
    });
  }

  abstract performVerification(
    sessionId: string,
    options?: {
      videoElement?: HTMLVideoElement;
      simulatedOutcome?: "SUCCESS" | "FAILURE";
    }
  ): Promise<LivenessVerificationResult>;

  async getResult(sessionId: string): Promise<LivenessVerificationResult> {
    const res = await api.get(`/kyc/liveness/session/${sessionId}`);
    return res.data;
  }

  async cancelSession(sessionId: string): Promise<void> {
    this.stopCamera();
    try {
      await api.post(`/kyc/liveness/session/${sessionId}/cancel`, {});
    } catch {
      // Ignore cancellation failures
    }
  }
}
