import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Bell,
  BellRing,
  CheckCheck,
  TrendingUp,
  Clock,
  CircleDollarSign,
  ArrowRight,
  Settings,
  X,
  BadgeCheck,
  Inbox,
  PiggyBank,
  ShieldCheck,
  CheckCircle2,
} from "lucide-react";
import dayjs from "dayjs";
import { toast } from "sonner";

import {
  useNotifications,
  useMarkNotificationRead,
  useMarkAllNotificationsRead,
  useNotificationPreferences,
  useSaveNotificationPreferences,
  useSubscribePush,
} from "@/user/api";
import {
  PageHeading,
  EasyXCard,
  EasyXLoader,
  EasyXEmptyState,
  EasyXButton,
} from "@/design/EasyX";

function iconFor(type) {
  if (type === "investment_matured") return CircleDollarSign;
  if (type === "maturity_reminder") return Clock;
  if (type === "automated_reminder") return BellRing;
  if (type?.includes("deposit")) return Inbox;
  if (type?.includes("kyc")) return BadgeCheck;
  if (type?.includes("investment")) return PiggyBank;
  return TrendingUp;
}

export default function NotificationsPage() {
  const navigate = useNavigate();
  const { data: notifications, isLoading } = useNotifications(false);
  const markRead = useMarkNotificationRead();
  const markAllRead = useMarkAllNotificationsRead();

  const { data: prefsData } = useNotificationPreferences();
  const savePrefs = useSaveNotificationPreferences();
  const subscribePush = useSubscribePush();

  const [prefsOpen, setPrefsOpen] = useState(false);
  const [prefsForm, setPrefsForm] = useState({
    kyc: true,
    deposit: true,
    investment: true,
    activity: true,
  });

  React.useEffect(() => {
    if (prefsData?.preferences) {
      setPrefsForm({
        kyc: prefsData.preferences.kyc !== false,
        deposit: prefsData.preferences.deposit !== false,
        investment: prefsData.preferences.investment !== false,
        activity: prefsData.preferences.activity !== false,
      });
    }
  }, [prefsData]);

  const hasUnread = (notifications || []).some((n) => !n.is_read);

  const handleActionClick = (notif) => {
    if (!notif.is_read) {
      markRead.mutate(notif.id);
    }
    if (notif.action_url) {
      navigate(notif.action_url);
    }
  };

  const handleSavePreferences = async () => {
    try {
      await savePrefs.mutateAsync(prefsForm);
      toast.success("Notification preferences updated.");
      setPrefsOpen(false);
    } catch (err) {
      toast.error("Failed to save preferences.");
    }
  };

  const handleEnablePush = async () => {
    if (!("Notification" in window)) {
      toast.error("Push notifications are not supported by this browser.");
      return;
    }

    try {
      const permission = await Notification.requestPermission();
      if (permission === "granted") {
        await subscribePush.mutateAsync({
          endpoint: "web-push-browser-token-" + Date.now(),
          keys: { auth: "demo-auth-token", p256dh: "demo-p256dh-key" },
          userAgent: navigator.userAgent,
        });
        toast.success("Push notifications enabled!");
      } else {
        toast.error("Push permission was dismissed or blocked.");
      }
    } catch (err) {
      toast.error("Failed to enable browser push.");
    }
  };

  return (
    <div data-testid="notifications-page">
      <PageHeading
        title="Notifications"
        subtitle="Account alerts, maturity updates, and important security reminders."
        icon={Bell}
        actions={
          <div className="flex items-center gap-2">
            <EasyXButton
              variant="outline"
              size="sm"
              onClick={() => setPrefsOpen(true)}
              data-testid="notification-preferences-btn"
              className="flex items-center gap-1.5 text-xs"
            >
              <Settings className="h-3.5 w-3.5" /> Preferences
            </EasyXButton>

            {hasUnread && (
              <EasyXButton
                variant="ghost"
                size="sm"
                onClick={() => markAllRead.mutate()}
                loading={markAllRead.isPending}
                data-testid="notifications-mark-all-read"
                className="flex items-center gap-1.5 text-xs"
              >
                <CheckCheck className="h-3.5 w-3.5" /> Mark all read
              </EasyXButton>
            )}
          </div>
        }
      />

      {isLoading ? (
        <EasyXLoader />
      ) : !notifications || notifications.length === 0 ? (
        <div className="mt-5">
          <EasyXEmptyState
            icon={Bell}
            title="No notifications yet"
            note="You'll be notified here when an investment is about to mature, when deposits are processed, and for important account milestones."
          />
        </div>
      ) : (
        <EasyXCard className="mt-5 p-0 overflow-hidden">
          <div className="divide-y divide-white/5">
            {notifications.map((n) => {
              const Icon = iconFor(n.type);
              const isReminder = n.type === "automated_reminder" || n.metadata?.is_reminder;

              return (
                <div
                  key={n.id}
                  data-testid={`notification-${n.id}`}
                  data-read={n.is_read ? "true" : "false"}
                  className={`flex items-start gap-3 px-4 py-4 transition ${
                    n.is_read ? "opacity-75" : "bg-white/[0.03]"
                  }`}
                >
                  <span
                    className={`mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-full ${
                      n.type === "investment_matured"
                        ? "bg-emerald-500/15 text-emerald-300"
                        : isReminder
                        ? "bg-ex-accent/20 text-ex-lav-300"
                        : "bg-white/10 text-ex-lav-200"
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                  </span>

                  <div className="min-w-0 flex-1 space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-ex-text">{n.title}</span>
                      {!n.is_read && (
                        <span className="h-2 w-2 shrink-0 rounded-full bg-ex-accent" aria-label="unread" />
                      )}
                    </div>
                    {n.body && <p className="text-sm text-ex-muted leading-relaxed">{n.body}</p>}

                    <div className="flex items-center gap-3 pt-1">
                      <span className="text-[11px] text-ex-muted font-mono">
                        {dayjs(n.created_at).format("DD MMM YYYY, HH:mm")}
                      </span>

                      {n.action_url && (
                        <button
                          type="button"
                          onClick={() => handleActionClick(n)}
                          className="inline-flex items-center gap-1 text-xs font-semibold text-ex-accent hover:underline"
                        >
                          {n.action_text || "Continue"} <ArrowRight className="h-3 w-3" />
                        </button>
                      )}
                    </div>
                  </div>

                  {!n.is_read && (
                    <button
                      onClick={() => markRead.mutate(n.id)}
                      className="shrink-0 rounded-ex-ctrl px-2.5 py-1 text-xs text-ex-muted hover:bg-white/8 hover:text-ex-text transition"
                      data-testid={`notification-read-${n.id}`}
                    >
                      Mark read
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </EasyXCard>
      )}

      {/* Preferences Drawer / Modal */}
      {prefsOpen && (
        <div className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4">
          <div className="w-full max-w-md rounded-2xl bg-ex-surface border border-white/10 p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <div className="flex items-center gap-2">
                <Settings className="h-5 w-5 text-ex-accent" />
                <h3 className="font-bold text-white text-base">Notification Preferences</h3>
              </div>
              <button
                onClick={() => setPrefsOpen(false)}
                className="text-ex-muted hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <p className="text-ex-muted">
                Choose which automated reminders and updates you want to receive.
              </p>

              <div className="divide-y divide-white/5 border border-white/5 rounded-xl bg-white/[0.02]">
                <label className="flex items-center justify-between p-3 cursor-pointer hover:bg-white/[0.02]">
                  <div>
                    <div className="font-semibold text-white">Deposit & Funding Alerts</div>
                    <div className="text-[11px] text-ex-muted">Reminders for unconfirmed deposits</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={prefsForm.deposit}
                    onChange={(e) => setPrefsForm({ ...prefsForm, deposit: e.target.checked })}
                    className="h-4 w-4 accent-ex-accent cursor-pointer"
                  />
                </label>

                <label className="flex items-center justify-between p-3 cursor-pointer hover:bg-white/[0.02]">
                  <div>
                    <div className="font-semibold text-white">Identity Verification (KYC)</div>
                    <div className="text-[11px] text-ex-muted">Reminders to complete KYC</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={prefsForm.kyc}
                    onChange={(e) => setPrefsForm({ ...prefsForm, kyc: e.target.checked })}
                    className="h-4 w-4 accent-ex-accent cursor-pointer"
                  />
                </label>

                <label className="flex items-center justify-between p-3 cursor-pointer hover:bg-white/[0.02]">
                  <div>
                    <div className="font-semibold text-white">Investment & Balance Opportunities</div>
                    <div className="text-[11px] text-ex-muted">Reminders for unallocated USDT balance</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={prefsForm.investment}
                    onChange={(e) => setPrefsForm({ ...prefsForm, investment: e.target.checked })}
                    className="h-4 w-4 accent-ex-accent cursor-pointer"
                  />
                </label>

                <label className="flex items-center justify-between p-3 cursor-pointer hover:bg-white/[0.02]">
                  <div>
                    <div className="font-semibold text-white">Platform Activity & Security</div>
                    <div className="text-[11px] text-ex-muted">Re-engagement & milestone reminders</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={prefsForm.activity}
                    onChange={(e) => setPrefsForm({ ...prefsForm, activity: e.target.checked })}
                    className="h-4 w-4 accent-ex-accent cursor-pointer"
                  />
                </label>
              </div>

              {/* Web Push Notification Enablement */}
              <div className="p-3 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-between">
                <div>
                  <div className="font-semibold text-purple-200">Browser Push Notifications</div>
                  <div className="text-[11px] text-purple-300/70">Receive instant alerts when away from app</div>
                </div>
                <EasyXButton
                  variant="outline"
                  size="sm"
                  onClick={handleEnablePush}
                  loading={subscribePush.isPending}
                  className="text-xs border-purple-500/30 text-purple-200 hover:bg-purple-500/20"
                >
                  Enable Push
                </EasyXButton>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-white/10">
              <EasyXButton
                variant="outline"
                size="sm"
                onClick={() => setPrefsOpen(false)}
              >
                Cancel
              </EasyXButton>
              <EasyXButton
                size="sm"
                onClick={handleSavePreferences}
                loading={savePrefs.isPending}
                className="bg-ex-accent text-ex-ink font-bold"
              >
                Save Preferences
              </EasyXButton>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
