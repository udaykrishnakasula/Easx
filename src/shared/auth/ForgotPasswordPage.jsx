import React, { useState, useEffect, useRef } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import {
  Loader2,
  Mail,
  KeyRound,
  ShieldCheck,
  ArrowLeft,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Eye,
  EyeOff,
  Lock,
  Sparkles,
  Info,
  Clock,
} from "lucide-react";

import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import { api, apiError } from "@/shared/lib/api";
import AuthLayout from "./AuthLayout";
import { FORGOT_PASSWORD, LOGIN } from "@/constants/testIds/auth";

export default function ForgotPasswordPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // Wizard Steps: 1 = Enter Email, 2 = Verify Code, 3 = New Password, 4 = Success
  const [step, setStep] = useState(1);

  // Form State
  const [email, setEmail] = useState("");
  const [maskedEmail, setMaskedEmail] = useState("");
  const [code, setCode] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [devCode, setDevCode] = useState("");

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Loading States
  const [requestingCode, setRequestingCode] = useState(false);
  const [verifyingCode, setVerifyingCode] = useState(false);
  const [resendingCode, setResendingCode] = useState(false);
  const [resettingPassword, setResettingPassword] = useState(false);

  // Timers
  const [cooldown, setCooldown] = useState(0);
  const [expiresIn, setExpiresIn] = useState(900); // 15 minutes default

  const codeInputRef = useRef(null);

  // Check URL params for direct reset link: ?email=...&token=...
  useEffect(() => {
    const urlEmail = searchParams.get("email");
    const urlToken = searchParams.get("token") || searchParams.get("reset_token");
    const urlCode = searchParams.get("code");

    if (urlEmail) {
      setEmail(urlEmail);
      setMaskedEmail(urlEmail);
    }

    if (urlEmail && (urlToken || urlCode)) {
      if (urlToken) setResetToken(urlToken);
      if (urlCode) setCode(urlCode);
      setStep(3); // Jump directly to new password step if token provided
    }
  }, [searchParams]);

  // Cooldown countdown timer
  useEffect(() => {
    if (cooldown <= 0) return;
    const interval = setInterval(() => {
      setCooldown((prev) => Math.max(0, prev - 1));
    }, 1000);
    return () => clearInterval(interval);
  }, [cooldown]);

  // Code expiration countdown timer (when on Step 2)
  useEffect(() => {
    if (step !== 2 || expiresIn <= 0) return;
    const interval = setInterval(() => {
      setExpiresIn((prev) => Math.max(0, prev - 1));
    }, 1000);
    return () => clearInterval(interval);
  }, [step, expiresIn]);

  // Auto-focus code input when step 2 opens
  useEffect(() => {
    if (step === 2 && codeInputRef.current) {
      codeInputRef.current.focus();
    }
  }, [step]);

  // Format expiration time (mm:ss)
  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s < 10 ? "0" : ""}${s}`;
  };

  // Password Strength Calculations
  const hasMinLength = newPassword.length >= 8;
  const hasNumber = /\d/.test(newPassword);
  const hasMixedCase = /[a-z]/.test(newPassword) && /[A-Z]/.test(newPassword);
  const hasSpecial = /[^A-Za-z0-9]/.test(newPassword);
  const passwordsMatch = newPassword && confirmPassword && newPassword === confirmPassword;

  const strengthScore = [hasMinLength, hasNumber, hasMixedCase, hasSpecial].filter(Boolean).length;

  const getStrengthMeta = () => {
    if (newPassword.length === 0) return { label: "None", color: "bg-white/10", textColor: "text-white/40" };
    if (strengthScore <= 1) return { label: "Weak", color: "bg-rose-500", textColor: "text-rose-400" };
    if (strengthScore <= 3) return { label: "Medium", color: "bg-amber-500", textColor: "text-amber-400" };
    return { label: "Strong & Secure", color: "bg-emerald-500", textColor: "text-emerald-400" };
  };

  // STEP 1: Request Reset Code via Email
  const handleRequestCode = async (e) => {
    e.preventDefault();
    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail) {
      toast.error("Please enter your account email address.");
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(cleanEmail)) {
      toast.error("Please enter a valid email format.");
      return;
    }

    setRequestingCode(true);
    try {
      const { data } = await api.post("/auth/forgot-password", { email: cleanEmail });
      toast.success(data.message || "Verification code sent to your email!");
      setMaskedEmail(data.email || cleanEmail);
      if (data.cooldown_seconds) setCooldown(data.cooldown_seconds);
      if (data.expires_in_minutes) setExpiresIn(data.expires_in_minutes * 60);
      if (data.reset_token) setResetToken(data.reset_token);
      if (data.dev_code) setDevCode(data.dev_code);
      setStep(2);
    } catch (err) {
      toast.error(apiError(err, "Failed to send reset code. Please try again."));
    } finally {
      setRequestingCode(false);
    }
  };

  // STEP 2: Verify Code
  const handleVerifyCode = async (e) => {
    if (e) e.preventDefault();
    const cleanCode = code.trim().replace(/\D/g, "");
    if (!cleanCode || cleanCode.length < 6) {
      toast.error("Please enter the complete 6-digit verification code.");
      return;
    }

    setVerifyingCode(true);
    try {
      const { data } = await api.post("/auth/verify-reset-code", {
        email: email.trim().toLowerCase(),
        code: cleanCode,
        token: resetToken,
      });
      toast.success(data.message || "Email verified successfully!");
      if (data.reset_token) setResetToken(data.reset_token);
      setStep(3);
    } catch (err) {
      toast.error(apiError(err, "Invalid or expired verification code."));
    } finally {
      setVerifyingCode(false);
    }
  };

  // STEP 2: Resend Code
  const handleResendCode = async () => {
    if (cooldown > 0) return;
    setResendingCode(true);
    try {
      const { data } = await api.post("/auth/resend-reset-code", {
        email: email.trim().toLowerCase(),
      });
      toast.success(data.message || "A new 6-digit verification code was sent.");
      if (data.cooldown_seconds) setCooldown(data.cooldown_seconds);
      if (data.expires_in_minutes) setExpiresIn(data.expires_in_minutes * 60);
      if (data.dev_code) setDevCode(data.dev_code);
      if (data.reset_token) setResetToken(data.reset_token);
      setCode("");
    } catch (err) {
      toast.error(apiError(err, "Failed to resend code."));
    } finally {
      setResendingCode(false);
    }
  };

  // STEP 3: Submit New Password
  const handleResetPassword = async (e) => {
    e.preventDefault();
    if (!newPassword || newPassword.length < 8) {
      toast.error("Password must be at least 8 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      toast.error("Passwords do not match. Please re-check.");
      return;
    }

    setResettingPassword(true);
    try {
      const { data } = await api.post("/auth/reset-password", {
        email: email.trim().toLowerCase(),
        code: code.trim(),
        reset_token: resetToken,
        token: resetToken,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });
      toast.success(data.message || "Password updated successfully!");
      setStep(4);
    } catch (err) {
      toast.error(apiError(err, "Failed to reset password."));
    } finally {
      setResettingPassword(false);
    }
  };

  // Auto-fill dev code for rapid testing
  const handleUseDevCode = () => {
    if (devCode) {
      setCode(devCode);
      toast.info("Auto-filled sandbox verification code.");
    }
  };

  return (
    <AuthLayout
      title={
        step === 1
          ? "Forgot Password"
          : step === 2
          ? "Verify Email"
          : step === 3
          ? "Create New Password"
          : "Password Reset Complete"
      }
      subtitle={
        step === 1
          ? "Enter your account email to receive a secure 6-digit reset code."
          : step === 2
          ? `We sent a 6-digit verification code to ${maskedEmail || email}.`
          : step === 3
          ? "Choose a strong password to secure your EasyX account."
          : "Your account is secured and ready for sign-in."
      }
      footer={
        step !== 4 ? (
          <Link
            to="/login"
            className="text-white inline-flex items-center gap-1.5 underline underline-offset-4 hover:text-purple-300 transition"
            data-testid={FORGOT_PASSWORD.backToLoginLink}
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Back to Sign In
          </Link>
        ) : null
      }
    >
      {/* Visual Step Progress Indicator */}
      <div className="flex items-center justify-between mb-6 px-1">
        {[
          { num: 1, label: "Email" },
          { num: 2, label: "Verify" },
          { num: 3, label: "New Password" },
        ].map((s, idx) => {
          const isDone = step > s.num || step === 4;
          const isCurrent = step === s.num;
          return (
            <React.Fragment key={s.num}>
              <div className="flex items-center gap-2">
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition ${
                    isDone
                      ? "bg-emerald-500 text-black shadow-lg shadow-emerald-500/20"
                      : isCurrent
                      ? "bg-purple-600 text-white ring-2 ring-purple-400 ring-offset-2 ring-offset-black/50"
                      : "bg-white/10 text-white/40 border border-white/10"
                  }`}
                >
                  {isDone ? <CheckCircle2 className="h-4 w-4" /> : s.num}
                </div>
                <span
                  className={`text-xs hidden sm:inline ${
                    isCurrent ? "font-bold text-white" : isDone ? "text-emerald-400" : "text-white/40"
                  }`}
                >
                  {s.label}
                </span>
              </div>
              {idx < 2 && (
                <div
                  className={`flex-1 h-[2px] mx-2 transition ${
                    step > idx + 1 ? "bg-emerald-500/60" : "bg-white/10"
                  }`}
                />
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* STEP 1: Enter Email */}
      {step === 1 && (
        <form onSubmit={handleRequestCode} className="space-y-4" data-testid="forgot-password-step-1">
          <div className="space-y-1.5">
            <Label htmlFor="forgot-email" className="text-white/80 flex items-center gap-1.5">
              <Mail className="h-3.5 w-3.5 text-purple-400" />
              Account Email
            </Label>
            <Input
              id="forgot-email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="bg-white/5 border-white/15 text-white placeholder:text-white/30 h-11 focus:border-purple-400"
              data-testid={FORGOT_PASSWORD.emailInput}
              required
              autoFocus
            />
          </div>

          <div className="p-3 rounded-xl bg-purple-950/20 border border-purple-500/20 text-xs text-purple-200/90 leading-relaxed flex items-start gap-2">
            <ShieldCheck className="h-4 w-4 text-purple-400 shrink-0 mt-0.5" />
            <span>
              For your account security, we'll send a 6-digit one-time verification code that expires in 15 minutes.
            </span>
          </div>

          <Button
            type="submit"
            disabled={requestingCode || !email.trim()}
            className="w-full bg-white text-black hover:bg-white/90 rounded-full h-11 font-semibold transition"
            data-testid={FORGOT_PASSWORD.submitButton}
          >
            {requestingCode ? (
              <span className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" /> Sending Verification Code...
              </span>
            ) : (
              "Send Verification Code"
            )}
          </Button>
        </form>
      )}

      {/* STEP 2: Verify Code */}
      {step === 2 && (
        <form onSubmit={handleVerifyCode} className="space-y-4" data-testid="forgot-password-step-2">
          {/* Target Email Info & Change Option */}
          <div className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/10 text-xs">
            <div className="flex items-center gap-2 truncate">
              <Mail className="h-4 w-4 text-purple-400 shrink-0" />
              <span className="text-white font-mono truncate">{maskedEmail || email}</span>
            </div>
            <button
              type="button"
              onClick={() => setStep(1)}
              className="text-purple-300 hover:text-white underline text-xs font-semibold shrink-0 ml-2"
            >
              Change
            </button>
          </div>

          {/* Verification Code Input */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <Label htmlFor="verification-code" className="text-white/80 flex items-center gap-1.5">
                <KeyRound className="h-3.5 w-3.5 text-purple-400" />
                6-Digit Verification Code
              </Label>
              {expiresIn > 0 ? (
                <span className="text-[11px] text-amber-300 flex items-center gap-1 font-mono">
                  <Clock className="h-3 w-3" /> Expires in {formatTime(expiresIn)}
                </span>
              ) : (
                <span className="text-[11px] text-rose-400 font-bold">Code Expired</span>
              )}
            </div>

            <Input
              id="verification-code"
              ref={codeInputRef}
              type="text"
              inputMode="numeric"
              maxLength={6}
              placeholder="123456"
              value={code}
              onChange={(e) => {
                const val = e.target.value.replace(/\D/g, "").slice(0, 6);
                setCode(val);
                if (val.length === 6) {
                  // Optional auto-trigger when 6 digits typed
                }
              }}
              className="bg-white/5 border-white/15 text-white placeholder:text-white/20 h-12 text-center font-mono text-xl tracking-[0.35em] font-bold focus:border-purple-400"
              data-testid={FORGOT_PASSWORD.codeInput}
              required
            />
          </div>

          {/* Dev/Sandbox Testing Helper */}
          {devCode && (
            <div className="p-2.5 rounded-xl bg-purple-950/30 border border-purple-500/30 text-xs text-purple-200 flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <Sparkles className="h-3.5 w-3.5 text-purple-400" />
                <span>Sandbox Verification Code:</span>
                <strong className="font-mono text-white text-sm bg-purple-900/60 px-1.5 py-0.5 rounded">
                  {devCode}
                </strong>
              </div>
              <button
                type="button"
                onClick={handleUseDevCode}
                className="text-[11px] px-2 py-0.5 rounded bg-purple-600 hover:bg-purple-500 text-white font-medium transition"
              >
                Auto-fill
              </button>
            </div>
          )}

          {/* Submit Verification Button */}
          <Button
            type="submit"
            disabled={verifyingCode || code.length < 6 || expiresIn <= 0}
            className="w-full bg-white text-black hover:bg-white/90 rounded-full h-11 font-semibold transition"
            data-testid={FORGOT_PASSWORD.verifyButton}
          >
            {verifyingCode ? (
              <span className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" /> Verifying Code...
              </span>
            ) : (
              "Verify Code & Continue"
            )}
          </Button>

          {/* Resend Code Button & Cooldown */}
          <div className="text-center pt-2">
            <button
              type="button"
              onClick={handleResendCode}
              disabled={cooldown > 0 || resendingCode}
              className={`text-xs inline-flex items-center gap-1.5 ${
                cooldown > 0
                  ? "text-white/40 cursor-not-allowed"
                  : "text-purple-300 hover:text-white underline font-medium"
              }`}
              data-testid={FORGOT_PASSWORD.resendButton}
            >
              <RefreshCw className={`h-3 w-3 ${resendingCode ? "animate-spin" : ""}`} />
              {cooldown > 0 ? `Resend new code in ${cooldown}s` : "Resend Verification Code"}
            </button>
          </div>
        </form>
      )}

      {/* STEP 3: Create New Password */}
      {step === 3 && (
        <form onSubmit={handleResetPassword} className="space-y-4" data-testid="forgot-password-step-3">
          {/* New Password */}
          <div className="space-y-1.5">
            <Label htmlFor="new-pwd" className="text-white/80 flex items-center gap-1.5">
              <Lock className="h-3.5 w-3.5 text-purple-400" />
              New Password
            </Label>
            <div className="relative">
              <Input
                id="new-pwd"
                type={showPassword ? "text" : "password"}
                placeholder="At least 8 characters"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="bg-white/5 border-white/15 text-white placeholder:text-white/30 h-11 pr-10 focus:border-purple-400"
                data-testid={FORGOT_PASSWORD.newPasswordInput}
                required
                autoFocus
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-white/50 hover:text-white p-1 focus:outline-none"
                aria-label={showPassword ? "Hide password" : "Show password"}
                title={showPassword ? "Hide password" : "Show password"}
                data-testid={FORGOT_PASSWORD.newPasswordToggle}
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          {/* Password Strength Indicator */}
          {newPassword.length > 0 && (
            <div className="space-y-2 p-3 rounded-xl bg-white/5 border border-white/10 text-xs">
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-white/60">Password Strength:</span>
                <span className={`font-bold ${getStrengthMeta().textColor}`}>
                  {getStrengthMeta().label}
                </span>
              </div>
              <div className="grid grid-cols-4 gap-1.5 h-1.5">
                {[1, 2, 3, 4].map((bar) => (
                  <div
                    key={bar}
                    className={`rounded-full transition-all duration-300 ${
                      strengthScore >= bar ? getStrengthMeta().color : "bg-white/10"
                    }`}
                  />
                ))}
              </div>
              <div className="grid grid-cols-2 gap-1.5 pt-1 text-[11px] text-white/70">
                <div className={`flex items-center gap-1 ${hasMinLength ? "text-emerald-400 font-semibold" : ""}`}>
                  <span className={hasMinLength ? "text-emerald-400" : "text-white/30"}>•</span> Min 8 chars
                </div>
                <div className={`flex items-center gap-1 ${hasNumber ? "text-emerald-400 font-semibold" : ""}`}>
                  <span className={hasNumber ? "text-emerald-400" : "text-white/30"}>•</span> Number (0-9)
                </div>
                <div className={`flex items-center gap-1 ${hasMixedCase ? "text-emerald-400 font-semibold" : ""}`}>
                  <span className={hasMixedCase ? "text-emerald-400" : "text-white/30"}>•</span> Upper & lowercase
                </div>
                <div className={`flex items-center gap-1 ${hasSpecial ? "text-emerald-400 font-semibold" : ""}`}>
                  <span className={hasSpecial ? "text-emerald-400" : "text-white/30"}>•</span> Special symbol
                </div>
              </div>
            </div>
          )}

          {/* Confirm Password */}
          <div className="space-y-1.5">
            <Label htmlFor="confirm-pwd" className="text-white/80 flex items-center gap-1.5">
              <ShieldCheck className="h-3.5 w-3.5 text-purple-400" />
              Confirm New Password
            </Label>
            <div className="relative">
              <Input
                id="confirm-pwd"
                type={showConfirmPassword ? "text" : "password"}
                placeholder="Re-type new password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className={`bg-white/5 border-white/15 text-white placeholder:text-white/30 h-11 pr-10 focus:border-purple-400 ${
                  confirmPassword && !passwordsMatch ? "border-rose-500 focus:border-rose-400" : ""
                }`}
                data-testid={FORGOT_PASSWORD.confirmPasswordInput}
                required
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-white/50 hover:text-white p-1 focus:outline-none"
                aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                title={showConfirmPassword ? "Hide password" : "Show password"}
                data-testid={FORGOT_PASSWORD.confirmPasswordToggle}
              >
                {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            {confirmPassword && !passwordsMatch && (
              <p className="text-xs text-rose-400 flex items-center gap-1 pt-0.5">
                <AlertCircle className="h-3 w-3" /> Passwords do not match
              </p>
            )}
            {passwordsMatch && (
              <p className="text-xs text-emerald-400 flex items-center gap-1 pt-0.5 font-medium">
                <CheckCircle2 className="h-3 w-3" /> Passwords match perfectly
              </p>
            )}
          </div>

          <Button
            type="submit"
            disabled={resettingPassword || !hasMinLength || !passwordsMatch}
            className="w-full bg-white text-black hover:bg-white/90 rounded-full h-11 font-semibold transition"
            data-testid={FORGOT_PASSWORD.resetSubmitButton}
          >
            {resettingPassword ? (
              <span className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" /> Updating Password...
              </span>
            ) : (
              "Save New Password"
            )}
          </Button>
        </form>
      )}

      {/* STEP 4: Reset Success */}
      {step === 4 && (
        <div className="space-y-5 text-center py-2" data-testid="forgot-password-step-4">
          <div className="w-16 h-16 rounded-full bg-emerald-500/10 border-2 border-emerald-500/30 text-emerald-400 flex items-center justify-center mx-auto shadow-lg shadow-emerald-500/10 animate-bounce">
            <CheckCircle2 className="h-8 w-8" />
          </div>

          <div className="space-y-1">
            <h3 className="text-lg font-bold text-white">Password Reset Successful!</h3>
            <p className="text-xs text-white/70 max-w-xs mx-auto">
              Your EasyX account password has been updated securely. You can now sign in with your new credentials.
            </p>
          </div>

          <div className="p-3 rounded-xl bg-white/5 border border-white/10 text-xs text-white/60">
            All previous active sessions and reset codes for this account have been invalidated for security.
          </div>

          <Button
            type="button"
            onClick={() => navigate("/login", { replace: true })}
            className="w-full bg-white text-black hover:bg-white/90 rounded-full h-11 font-semibold transition"
            data-testid={FORGOT_PASSWORD.successSignInButton}
          >
            Sign In with New Password
          </Button>
        </div>
      )}
    </AuthLayout>
  );
}
