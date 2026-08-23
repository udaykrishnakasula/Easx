import React, { useState } from "react";
import { Lock, ArrowRight, TrendingUp, Plus } from "lucide-react";
import dayjs from "dayjs";
import { useNavigate } from "react-router-dom";

import { PLAN_THEME } from "./plan-theme";
import { money } from "./api";
import { EasyXStatusBadge, EasyXButton } from "@/design/EasyX";
import BuyPlanDialog from "./BuyPlanDialog";

export default function PlanCard({ plan, userName, walletBalance }) {
  const theme = PLAN_THEME[plan.key] || PLAN_THEME.silver;
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();

  return (
    <>
      <div
        className="relative overflow-hidden rounded-ex border border-white/8 p-5 min-h-[280px] flex flex-col ex-hover"
        data-testid={`dash-plan-${plan.key}`}
        data-unlocked={plan.unlocked ? "true" : "false"}
        style={{ background: theme.surface, boxShadow: `0 24px 60px -34px ${theme.glow}` }}
      >
        {/* top accent line */}
        <div className="absolute inset-x-0 top-0 h-px" style={{ background: `linear-gradient(90deg, transparent, ${theme.accent}55, transparent)` }} />

        <div className="flex items-center justify-between">
          <span className={`ex-eyebrow ${theme.label}`}>{plan.name}</span>
          <EasyXStatusBadge status={plan.unlocked ? "unlocked" : "locked"} />
        </div>

        {plan.unlocked ? (
          <UnlockedBody plan={plan} theme={theme} userName={userName}
            onView={() => navigate(`/app/investments?plan=${plan.key}`)} onBuyMore={() => setOpen(true)} />
        ) : (
          <LockedBody plan={plan} onUnlock={() => setOpen(true)} />
        )}
      </div>

      <BuyPlanDialog plan={plan} open={open} onOpenChange={setOpen} walletBalance={walletBalance} />
    </>
  );
}

function LockedBody({ plan, onUnlock }) {
  return (
    <div className="relative flex-1 mt-4">
      {/* Info hidden behind a light ~10% frost */}
      <div className="pointer-events-none select-none blur-[2px] opacity-70" aria-hidden="true">
        <div className="ex-display text-3xl font-extrabold text-white">{money(plan.price)}</div>
        <div className="mt-3 space-y-2 text-sm text-white/80">
          <div>{plan.lock_days} days lock</div>
          <div>Profit {plan.profit_percentage}%</div>
          <div>Maturity {money(plan.maturity_amount)}</div>
          <div>Expected profit {money(plan.profit_amount)}</div>
        </div>
      </div>
      {/* Light-frost overlay + flat 2D yellow lock */}
      <button
        onClick={onUnlock}
        data-testid={`dash-plan-unlock-${plan.key}`}
        className="absolute inset-0 flex flex-col items-center justify-center gap-2 rounded-2xl border border-white/8 bg-white/[0.03] backdrop-blur-[3px] transition hover:bg-white/[0.06]"
      >
        <Lock className="h-11 w-11 text-yellow-400" strokeWidth={2.25} />
        <span className="text-sm font-semibold text-white ex-display">Tap to unlock</span>
        <span className="text-xs text-ex-muted">Invest to reveal this plan</span>
      </button>
    </div>
  );
}

function UnlockedBody({ plan, userName, onView, onBuyMore }) {
  return (
    <div className="mt-2 flex flex-1 flex-col">
      <p className="text-xs text-ex-muted">Welcome, {userName}</p>
      <div className="mt-1 flex items-baseline gap-2">
        <span className="ex-display text-2xl font-extrabold text-white">{plan.cards}</span>
        <span className="text-sm text-ex-muted">Card{plan.cards === 1 ? "" : "s"}</span>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-y-2.5 text-sm">
        <Stat label="Total invested" value={money(plan.total_invested)} />
        <Stat label="Active" value={plan.active_investments} />
        <Stat label="Expected profit" value={money(plan.expected_profit)} accent />
        <Stat label="Expected maturity" value={money(plan.expected_maturity)} />
        <Stat label="Next maturity" value={plan.next_maturity ? dayjs(plan.next_maturity).format("DD MMM YYYY") : "—"} full />
      </div>
      <div className="mt-auto flex gap-2 pt-4">
        <EasyXButton onClick={onView} data-testid={`dash-view-${plan.key}`} className="flex-1 h-9">
          View Investments <ArrowRight className="ml-1 h-4 w-4" />
        </EasyXButton>
        <EasyXButton variant="ghost" onClick={onBuyMore} data-testid={`dash-buymore-${plan.key}`} className="h-9 px-3">
          <Plus className="h-4 w-4" />
        </EasyXButton>
      </div>
    </div>
  );
}

function Stat({ label, value, accent, full }) {
  return (
    <div className={full ? "col-span-2" : ""}>
      <div className="text-[11px] uppercase tracking-wide text-ex-muted/70">{label}</div>
      <div className={`font-semibold ${accent ? "text-emerald-300" : "text-white"} flex items-center gap-1`}>
        {accent && <TrendingUp className="h-3.5 w-3.5" />}{value}
      </div>
    </div>
  );
}
