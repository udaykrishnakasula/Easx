import React, { useState, useEffect } from "react";
import {
  User,
  Mail,
  Phone,
  Hash,
  ShieldCheck,
  KeyRound,
  Bell,
  Save,
  Copy,
  Check,
  CheckCircle2,
  Lock,
  Sparkles,
  ExternalLink,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/shared/context/AuthContext";
import { PageHeading, EasyXCard, EasyXButton, EasyXStatusBadge } from "@/design/EasyX";
import {
  updateUserProfile,
  changeUserPassword,
  useNotificationPreferences,
  useSaveNotificationPreferences,
} from "@/user/api";
import { notifySuccess, notifyError, notifySettingsUpdated } from "@/shared/lib/toastFeedback";

export default function ProfilePage() {
  const { user } = useAuth();
  const navigate = useNavigate();

  // Profile Information State
  const [name, setName] = useState(user?.name || "");
  const [phone, setPhone] = useState(user?.phone || "");
  const [savingProfile, setSavingProfile] = useState(false);

  useEffect(() => {
    if (user?.name) setName(user.name);
    if (user?.phone) setPhone(user.phone);
  }, [user]);

  // Security / Password State
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [changingPassword, setChangingPassword] = useState(false);

  // Referral Copy State
  const [copiedRefCode, setCopiedRefCode] = useState(false);
  const [copiedRefLink, setCopiedRefLink] = useState(false);

  const origin = typeof window !== "undefined" ? window.location.origin : "";
  const referralLink = user?.referral_code ? `${origin}/register?ref=${user.referral_code}` : "";

  // Notification Preferences State & Hook
  const { data: notifData } = useNotificationPreferences();
  const updateNotifMutation = useSaveNotificationPreferences();

  const [prefs, setPrefs] = useState({
    kyc: true,
    deposit: true,
    investment: true,
    activity: true,
  });

  useEffect(() => {
    if (notifData?.preferences) {
      setPrefs({
        kyc: notifData.preferences.kyc !== false,
        deposit: notifData.preferences.deposit !== false,
        investment: notifData.preferences.investment !== false,
        activity: notifData.preferences.activity !== false,
      });
    }
  }, [notifData]);

  // Handler: Save Profile Details
  const handleSaveProfile = async (e) => {
    e?.preventDefault();
    if (!name.trim()) {
      notifyError("Name is required", "Please enter your full name.");
      return;
    }

    setSavingProfile(true);
    try {
      await updateUserProfile({ name, phone });
      notifySettingsUpdated("Profile details");
    } catch (err) {
      notifyError(
        "Failed to update profile",
        err?.response?.data?.detail || "Could not save your changes. Please try again."
      );
    } finally {
      setSavingProfile(false);
    }
  };

  // Handler: Change Password
  const handleChangePassword = async (e) => {
    e?.preventDefault();
    if (!currentPassword) {
      notifyError("Current password required", "Please enter your current password.");
      return;
    }
    if (newPassword.length < 8) {
      notifyError("Password too short", "New password must be at least 8 characters long.");
      return;
    }
    if (newPassword !== confirmPassword) {
      notifyError("Passwords do not match", "Please ensure your new password matches the confirmation.");
      return;
    }

    setChangingPassword(true);
    try {
      await changeUserPassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      notifySuccess("Password changed successfully", "Your account security credentials have been updated.");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      notifyError(
        "Could not update password",
        err?.response?.data?.detail || "Please check your current password and try again."
      );
    } finally {
      setChangingPassword(false);
    }
  };

  // Handler: Toggle Notification Preference
  const handleTogglePref = async (key) => {
    const updated = { ...prefs, [key]: !prefs[key] };
    setPrefs(updated);
    try {
      await updateNotifMutation.mutateAsync(updated);
      notifySuccess(
        "Notification settings updated",
        `${key.charAt(0).toUpperCase() + key.slice(1)} notification preferences saved.`
      );
    } catch {
      notifyError("Could not update preference");
    }
  };

  // Handler: Copy Referral Code
  const handleCopyCode = async () => {
    if (!user?.referral_code) return;
    try {
      await navigator.clipboard.writeText(user.referral_code);
      setCopiedRefCode(true);
      notifySuccess("Referral code copied!", `Code ${user.referral_code} ready to share.`);
      setTimeout(() => setCopiedRefCode(false), 2000);
    } catch {
      notifyError("Failed to copy code");
    }
  };

  // Handler: Copy Referral Link
  const handleCopyLink = async () => {
    if (!referralLink) return;
    try {
      await navigator.clipboard.writeText(referralLink);
      setCopiedRefLink(true);
      notifySuccess("Referral link copied!", "Link copied to clipboard for 10% commission sharing.");
      setTimeout(() => setCopiedRefLink(false), 2000);
    } catch {
      notifyError("Failed to copy link");
    }
  };

  return (
    <div data-testid="profile-page" className="max-w-5xl mx-auto space-y-6">
      <PageHeading
        title="Account & Profile Settings"
        subtitle="Manage your personal information, security credentials, and alert preferences."
        icon={User}
      />

      {/* Grid: Profile Details & KYC Status */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2 Cols): Personal Information Editor */}
        <div className="lg:col-span-2 space-y-6">
          {/* Personal Information Form */}
          <EasyXCard>
            <div className="flex items-center justify-between border-b border-white/8 pb-4 mb-5">
              <div className="flex items-center gap-3">
                <div className="grid h-9 w-9 place-items-center rounded-xl bg-ex-lav-400/20 text-ex-lav-300">
                  <User className="h-4 w-4" />
                </div>
                <div>
                  <h2 className="text-sm font-semibold text-white">Personal Information</h2>
                  <p className="text-xs text-ex-muted">Update your display name and contact details.</p>
                </div>
              </div>
            </div>

            <form onSubmit={handleSaveProfile} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-ex-muted mb-1.5">
                  Full Name
                </label>
                <div className="relative">
                  <User className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-ex-muted" />
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Your Full Name"
                    className="w-full rounded-xl bg-white/5 border border-white/10 pl-10 pr-4 py-2.5 text-sm text-white placeholder:text-white/30 focus:border-ex-lav-400 focus:outline-none transition-colors"
                    data-testid="profile-name-input"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-ex-muted mb-1.5">
                    Email Address
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-ex-muted" />
                    <input
                      type="email"
                      value={user?.email || ""}
                      disabled
                      className="w-full rounded-xl bg-white/[0.02] border border-white/5 pl-10 pr-4 py-2.5 text-sm text-ex-muted cursor-not-allowed"
                    />
                  </div>
                  <span className="text-[11px] text-ex-muted/60 mt-1 block">
                    Account email is primary identifier and cannot be changed.
                  </span>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-ex-muted mb-1.5">
                    Phone Number
                  </label>
                  <div className="relative">
                    <Phone className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-ex-muted" />
                    <input
                      type="tel"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      placeholder="+1 (555) 000-0000"
                      className="w-full rounded-xl bg-white/5 border border-white/10 pl-10 pr-4 py-2.5 text-sm text-white placeholder:text-white/30 focus:border-ex-lav-400 focus:outline-none transition-colors"
                      data-testid="profile-phone-input"
                    />
                  </div>
                </div>
              </div>

              <div className="flex justify-end pt-2">
                <EasyXButton
                  type="submit"
                  variant="primary"
                  className="h-10 px-5 text-xs font-semibold flex items-center gap-2"
                  disabled={savingProfile}
                  data-testid="save-profile-btn"
                >
                  <Save className="h-3.5 w-3.5" />
                  {savingProfile ? "Saving..." : "Save Changes"}
                </EasyXButton>
              </div>
            </form>
          </EasyXCard>

          {/* Security / Password Card */}
          <EasyXCard>
            <div className="flex items-center justify-between border-b border-white/8 pb-4 mb-5">
              <div className="flex items-center gap-3">
                <div className="grid h-9 w-9 place-items-center rounded-xl bg-amber-500/10 text-amber-400">
                  <KeyRound className="h-4 w-4" />
                </div>
                <div>
                  <h2 className="text-sm font-semibold text-white">Password & Security</h2>
                  <p className="text-xs text-ex-muted">Ensure your account remains secure with a strong password.</p>
                </div>
              </div>
            </div>

            <form onSubmit={handleChangePassword} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-ex-muted mb-1.5">
                  Current Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-ex-muted" />
                  <input
                    type="password"
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full rounded-xl bg-white/5 border border-white/10 pl-10 pr-4 py-2.5 text-sm text-white placeholder:text-white/30 focus:border-ex-lav-400 focus:outline-none transition-colors"
                    data-testid="current-password-input"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-ex-muted mb-1.5">
                    New Password
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-ex-muted" />
                    <input
                      type="password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="Minimum 8 characters"
                      className="w-full rounded-xl bg-white/5 border border-white/10 pl-10 pr-4 py-2.5 text-sm text-white placeholder:text-white/30 focus:border-ex-lav-400 focus:outline-none transition-colors"
                      data-testid="new-password-input"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-ex-muted mb-1.5">
                    Confirm New Password
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-ex-muted" />
                    <input
                      type="password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="Re-enter new password"
                      className="w-full rounded-xl bg-white/5 border border-white/10 pl-10 pr-4 py-2.5 text-sm text-white placeholder:text-white/30 focus:border-ex-lav-400 focus:outline-none transition-colors"
                      data-testid="confirm-password-input"
                    />
                  </div>
                </div>
              </div>

              <div className="flex justify-end pt-2">
                <EasyXButton
                  type="submit"
                  variant="ghost"
                  className="h-10 px-5 text-xs font-semibold border border-white/10 hover:bg-white/10 flex items-center gap-2"
                  disabled={changingPassword}
                  data-testid="change-password-btn"
                >
                  <KeyRound className="h-3.5 w-3.5" />
                  {changingPassword ? "Updating..." : "Update Password"}
                </EasyXButton>
              </div>
            </form>
          </EasyXCard>
        </div>

        {/* Right Column: KYC Status, Referral Info & Notification Toggles */}
        <div className="space-y-6">
          {/* Identity Verification Summary Card */}
          <EasyXCard>
            <div className="flex items-center gap-3 mb-4">
              <div className="grid h-9 w-9 place-items-center rounded-xl bg-emerald-500/10 text-emerald-400">
                <ShieldCheck className="h-4 w-4" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-white">Identity Verification</h3>
                <p className="text-xs text-ex-muted">KYC & Compliance Status</p>
              </div>
            </div>

            <div className="rounded-xl border border-white/8 bg-white/[0.02] p-4 flex items-center justify-between">
              <div>
                <div className="text-xs text-ex-muted">Tier Status</div>
                <div className="font-semibold text-white text-sm mt-0.5 capitalize">
                  {user?.kyc_tier ? `${user.kyc_tier} Tier` : "Standard Tier"}
                </div>
              </div>
              <EasyXStatusBadge status={user?.kyc_status === "approved" ? "approved" : "pending"} />
            </div>

            <div className="mt-4">
              <EasyXButton
                variant="ghost"
                className="w-full h-9 text-xs border border-white/10 hover:bg-white/10 flex items-center justify-center gap-1.5"
                onClick={() => navigate("/kyc")}
              >
                <span>View Verification Details</span>
                <ExternalLink className="h-3.5 w-3.5" />
              </EasyXButton>
            </div>
          </EasyXCard>

          {/* Referral Code Quick Copy Card */}
          <EasyXCard>
            <div className="flex items-center gap-3 mb-4">
              <div className="grid h-9 w-9 place-items-center rounded-xl bg-ex-lav-400/20 text-ex-lav-300">
                <Hash className="h-4 w-4" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-white">Your Referral Code</h3>
                <p className="text-xs text-ex-muted">Share to earn 10% instant commission</p>
              </div>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between rounded-xl border border-white/8 bg-white/[0.03] p-3">
                <span className="font-mono text-sm font-bold text-white tracking-wider">
                  {user?.referral_code || "—"}
                </span>
                <EasyXButton
                  variant="ghost"
                  className="h-8 px-2.5 text-xs"
                  onClick={handleCopyCode}
                  data-testid="copy-profile-ref-code"
                >
                  {copiedRefCode ? (
                    <Check className="h-3.5 w-3.5 text-emerald-400" />
                  ) : (
                    <Copy className="h-3.5 w-3.5 text-ex-muted" />
                  )}
                </EasyXButton>
              </div>

              <EasyXButton
                variant="accent"
                className="w-full h-9 text-xs font-semibold flex items-center justify-center gap-2"
                onClick={handleCopyLink}
                data-testid="copy-profile-ref-link"
              >
                {copiedRefLink ? (
                  <>
                    <Check className="h-3.5 w-3.5 text-emerald-300" /> Referral Link Copied!
                  </>
                ) : (
                  <>
                    <Copy className="h-3.5 w-3.5" /> Copy Referral Link
                  </>
                )}
              </EasyXButton>
            </div>
          </EasyXCard>

          {/* Notification Preferences Card */}
          <EasyXCard>
            <div className="flex items-center gap-3 mb-4">
              <div className="grid h-9 w-9 place-items-center rounded-xl bg-ex-accent/15 text-ex-accent">
                <Bell className="h-4 w-4" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-white">Alert Preferences</h3>
                <p className="text-xs text-ex-muted">Instant event notifications</p>
              </div>
            </div>

            <div className="space-y-3">
              {[
                { id: "investment", label: "Investment Returns", desc: "Daily yield & maturity alerts" },
                { id: "deposit", label: "Deposits & Withdrawals", desc: "Blockchain confirmations" },
                { id: "kyc", label: "KYC Verifications", desc: "Identity status updates" },
                { id: "activity", label: "Security & Logins", desc: "Account security alerts" },
              ].map(({ id, label, desc }) => (
                <div
                  key={id}
                  className="flex items-center justify-between rounded-xl border border-white/5 bg-white/[0.02] p-3 transition-colors hover:bg-white/[0.04]"
                >
                  <div>
                    <div className="text-xs font-semibold text-white">{label}</div>
                    <div className="text-[11px] text-ex-muted">{desc}</div>
                  </div>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={prefs[id]}
                    onClick={() => handleTogglePref(id)}
                    className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                      prefs[id] ? "bg-ex-accent" : "bg-white/10"
                    }`}
                  >
                    <span
                      className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-lg ring-0 transition duration-200 ease-in-out ${
                        prefs[id] ? "translate-x-4 bg-ex-ink" : "translate-x-0 bg-white/70"
                      }`}
                    />
                  </button>
                </div>
              ))}
            </div>
          </EasyXCard>
        </div>
      </div>
    </div>
  );
}
