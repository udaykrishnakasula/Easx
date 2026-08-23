import React from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { ShieldCheck, Inbox, Settings, ArrowLeft, LogOut, BadgeCheck, Share2, Users, Wrench, LayoutDashboard, ArrowUpFromLine, PiggyBank, Layers, Download } from "lucide-react";

import { useAuth } from "@/context/AuthContext";

const NAV = [
  { to: "/admin/overview", label: "Overview", icon: LayoutDashboard },
  { to: "/admin/users", label: "Users", icon: Users },
  { to: "/admin/deposits", label: "Deposits", icon: Inbox },
  { to: "/admin/withdrawals", label: "Withdrawals", icon: ArrowUpFromLine },
  { to: "/admin/investments", label: "Investments", icon: PiggyBank },
  { to: "/admin/plans", label: "Plans", icon: Layers },
  { to: "/admin/kyc", label: "KYC Review", icon: BadgeCheck },
  { to: "/admin/referrals", label: "Referrals", icon: Share2 },
  { to: "/admin/reports", label: "Reports & Audit", icon: Download },
  { to: "/admin/maintenance", label: "Maintenance", icon: Wrench },
  { to: "/admin/settings", label: "Deposit Settings", icon: Settings },
];

export default function AdminLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-ex-bg text-ex-text flex">
      <aside className="hidden md:flex w-64 shrink-0 flex-col border-r border-white/8 bg-ex-surface/60 p-4">
        <div className="flex items-center gap-2 px-2 py-1">
          <span className="grid h-9 w-9 place-items-center rounded-ex-ctrl bg-ex-accent text-ex-ink">
            <ShieldCheck className="h-5 w-5" />
          </span>
          <div>
            <div className="ex-display font-extrabold leading-none">EasyX</div>
            <div className="text-[11px] text-ex-muted">Admin console</div>
          </div>
        </div>

        <nav className="mt-7 flex flex-col gap-1" data-testid="admin-nav">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-ex-ctrl px-3 py-2.5 text-sm transition ${
                  isActive
                    ? "bg-ex-accent text-ex-ink font-semibold shadow-ex-btn"
                    : "text-ex-muted hover:bg-white/8 hover:text-ex-text"
                }`
              }
            >
              <Icon className="h-4 w-4" /> {label}
            </NavLink>
          ))}
        </nav>

        <div className="mt-auto flex flex-col gap-1">
          <button
            onClick={() => navigate("/app/dashboard")}
            className="flex items-center gap-3 rounded-ex-ctrl px-3 py-2.5 text-sm text-ex-muted hover:bg-white/8 hover:text-ex-text"
          >
            <ArrowLeft className="h-4 w-4" /> Back to app
          </button>
          <button
            onClick={() => {
              logout();
              navigate("/login");
            }}
            className="flex items-center gap-3 rounded-ex-ctrl px-3 py-2.5 text-sm text-ex-muted hover:bg-white/8 hover:text-ex-text"
          >
            <LogOut className="h-4 w-4" /> Sign out
          </button>
        </div>
      </aside>

      <div className="flex-1 min-w-0">
        <header className="flex items-center justify-between border-b border-white/8 px-5 py-4 md:hidden">
          <div className="ex-display font-extrabold">EasyX Admin</div>
          <button onClick={() => navigate("/app/dashboard")} className="text-sm text-ex-muted">Back to app</button>
        </header>
        <main className="p-5 sm:p-8 max-w-5xl mx-auto">
          <div className="mb-4 text-xs text-ex-muted">Signed in as {user?.email}</div>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
