import React, { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  ShieldCheck,
  Inbox,
  Settings,
  ArrowLeft,
  LogOut,
  BadgeCheck,
  Share2,
  Users,
  LayoutDashboard,
  ArrowUpFromLine,
  PiggyBank,
  CalendarClock,
  Layers,
  Download,
  ScrollText,
  Wallet,
  Menu,
  X,
} from "lucide-react";

import { useAuth } from "@/shared/context/AuthContext";

const ADMIN_NAV = [
  { to: "/admin", label: "Overview", icon: LayoutDashboard },
  { to: "/admin/users", label: "Users", icon: Users },
  { to: "/admin/deposits", label: "Deposits", icon: Inbox },
  { to: "/admin/investments", label: "Investments", icon: PiggyBank },
  { to: "/admin/maturities", label: "Maturities", icon: CalendarClock },
  { to: "/admin/withdrawals", label: "Withdrawals", icon: ArrowUpFromLine },
  { to: "/admin/kyc", label: "KYC", icon: BadgeCheck },
  { to: "/admin/referrals", label: "Referrals", icon: Share2 },
  { to: "/admin/plans", label: "Plans", icon: Layers },
  { to: "/admin/wallet", label: "Wallet", icon: Wallet },
  { to: "/admin/reports", label: "Reports", icon: Download },
  { to: "/admin/audit", label: "Audit Logs", icon: ScrollText },
  { to: "/admin/settings", label: "Settings", icon: Settings },
];

export default function AdminLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-ex-bg text-ex-text flex">
      {/* Desktop Sidebar (Admin Navigation Only) */}
      <aside className="hidden md:flex w-64 shrink-0 flex-col border-r border-white/8 bg-ex-surface/60 p-4 sticky top-0 h-screen">
        <div className="flex items-center gap-2.5 px-2 py-1.5">
          <span className="grid h-9 w-9 place-items-center rounded-ex-ctrl bg-ex-accent text-ex-ink shadow-sm">
            <ShieldCheck className="h-5 w-5" />
          </span>
          <div>
            <div className="ex-display font-extrabold leading-none tracking-tight">EasyX</div>
            <div className="text-[11px] font-medium text-ex-muted mt-0.5">Admin console</div>
          </div>
        </div>

        <div className="mt-4 px-2 py-2 rounded-ex bg-white/[0.03] border border-white/5 text-[11px] text-ex-muted">
          Logged in as <strong className="text-ex-text block truncate">{user?.email}</strong>
        </div>

        <nav className="mt-4 space-y-1 flex-1 overflow-y-auto pr-1">
          {ADMIN_NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/admin"}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-ex-ctrl text-xs font-semibold transition ${
                  isActive
                    ? "bg-ex-accent text-ex-ink shadow-sm"
                    : "text-ex-muted hover:text-white hover:bg-white/5"
                }`
              }
            >
              <item.icon className="h-4 w-4 shrink-0" />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="pt-3 mt-2 border-t border-white/10 space-y-1.5">
          <button
            onClick={() => navigate("/dashboard")}
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-ex-ctrl text-xs font-medium text-ex-muted hover:text-white hover:bg-white/5 transition"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Switch to User View</span>
          </button>
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-ex-ctrl text-xs font-medium text-red-400 hover:text-red-300 hover:bg-red-500/10 transition"
          >
            <LogOut className="h-4 w-4" />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* Main Container */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile Top Header */}
        <header className="md:hidden flex items-center justify-between border-b border-white/10 bg-ex-surface p-4 sticky top-0 z-30">
          <div className="flex items-center gap-2">
            <span className="grid h-8 w-8 place-items-center rounded-ex-ctrl bg-ex-accent text-ex-ink shadow-sm">
              <ShieldCheck className="h-4 w-4" />
            </span>
            <span className="font-bold text-sm">EasyX Admin</span>
          </div>
          <button
            onClick={() => setMobileNavOpen(!mobileNavOpen)}
            className="p-2 rounded-ex-ctrl bg-white/5 text-ex-text hover:bg-white/10"
          >
            {mobileNavOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </header>

        {/* Mobile Sliding Navigation */}
        {mobileNavOpen && (
          <div className="md:hidden fixed inset-0 top-16 bg-ex-bg/95 backdrop-blur-md z-40 p-4 overflow-y-auto space-y-1 flex flex-col">
            {ADMIN_NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/admin"}
                onClick={() => setMobileNavOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-ex-ctrl text-sm font-semibold transition ${
                    isActive
                      ? "bg-ex-accent text-ex-ink shadow-sm"
                      : "text-ex-muted hover:text-white hover:bg-white/5"
                  }`
                }
              >
                <item.icon className="h-4 w-4 shrink-0" />
                <span>{item.label}</span>
              </NavLink>
            ))}
            <div className="pt-4 mt-auto border-t border-white/10 space-y-2">
              <button
                onClick={() => {
                  setMobileNavOpen(false);
                  navigate("/dashboard");
                }}
                className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-ex-ctrl text-sm font-medium text-ex-muted hover:text-white hover:bg-white/5 transition"
              >
                <ArrowLeft className="h-4 w-4" />
                <span>Switch to User View</span>
              </button>
              <button
                onClick={handleLogout}
                className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-ex-ctrl text-sm font-medium text-red-400 hover:text-red-300 hover:bg-red-500/10 transition"
              >
                <LogOut className="h-4 w-4" />
                <span>Sign Out</span>
              </button>
            </div>
          </div>
        )}

        {/* Content Area */}
        <main className="flex-1 p-4 md:p-8 max-w-7xl w-full mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
