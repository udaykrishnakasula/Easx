import React from "react";
import { Wallet as WalletIcon, TrendingUp, Layers } from "lucide-react";

import { useDashboard, money } from "./api";
import DashboardPlanCarousel from "./DashboardPlanCarousel";
import RewardsFeed from "./RewardsFeed";
import { EasyXStat, Eyebrow, EasyXLoader, EasyXEmptyState } from "@/design/EasyX";

export default function DashboardHome() {
  const { data, isLoading, isError } = useDashboard();

  if (isLoading) return <EasyXLoader className="py-24" />;
  if (isError || !data) {
    return <EasyXEmptyState icon={WalletIcon} title="Could not load your dashboard" note="Please refresh the page." />;
  }

  const { user, wallet, plans } = data;

  return (
    <div data-testid="dashboard-home">
      {/* Intro — "the landing, after entering the product" */}
      <div className="relative overflow-hidden rounded-ex-lg border border-white/8 p-6 sm:p-8"
        style={{ background: "radial-gradient(120% 140% at 100% 0%, rgba(150,128,220,0.22) 0%, rgba(23,22,29,0) 55%), linear-gradient(160deg,#17161d,#0c0c0f)" }}>
        <Eyebrow>Your EasyX portfolio</Eyebrow>
        <h1 className="mt-2 ex-display text-3xl sm:text-4xl font-extrabold tracking-tight leading-[1.02]">
          Welcome, <span className="ex-accent-text">{user.name?.split(" ")[0]}</span>
        </h1>
        <p className="mt-2 text-ex-muted text-sm sm:text-base max-w-md">
          Grow your USDT with EasyX investment plans. Your wealth works while you rest.
        </p>
      </div>

      {/* Three balances: Available, Locked Investment, Total Portfolio */}
      <div className="mt-5 grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4">
        <div data-testid="summary-wallet"><EasyXStat label="Available balance" value={money(wallet.available_balance)} icon={WalletIcon} gradient /></div>
        <EasyXStat label="Locked investment" value={money(wallet.locked_investment)} icon={Layers} />
        <EasyXStat label="Total portfolio" value={money(wallet.total_portfolio)} icon={TrendingUp} gradient />
      </div>

      {/* Plan cards — same 3D certificate carousel as the landing page */}
      <div className="mt-9 flex items-end justify-between">
        <div>
          <Eyebrow>Investment plans</Eyebrow>
          <h2 className="mt-1 ex-display text-xl sm:text-2xl font-extrabold">Choose your tier</h2>
        </div>
        <span className="text-xs text-ex-muted">1 card = 1 investment</span>
      </div>
      <DashboardPlanCarousel plans={plans} walletBalance={wallet.available_balance} userName={user.name} />

      {/* Live rewards & payouts activity feed */}
      <RewardsFeed />
    </div>
  );
}
