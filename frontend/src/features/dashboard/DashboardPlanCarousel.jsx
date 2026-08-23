import React, { useRef, useState } from "react";
import Autoplay from "embla-carousel-autoplay";
import { Lock, ArrowRight, Plus } from "lucide-react";
import { useNavigate } from "react-router-dom";

import {
  Carousel, CarouselContent, CarouselItem, CarouselPrevious, CarouselNext,
} from "@/components/ui/carousel";
import { InvestmentCard } from "@/components/landing/DiamondInvestmentCard";
import { EasyXButton, EasyXStatusBadge } from "@/design/EasyX";
import BuyPlanDialog from "./BuyPlanDialog";
import { money } from "./api";

const ORDER = ["silver", "gold", "platinum", "diamond"];

export default function DashboardPlanCarousel({ plans, walletBalance, userName }) {
  const navigate = useNavigate();
  const [buyPlan, setBuyPlan] = useState(null);

  const autoplay = useRef(null);
  if (!autoplay.current) {
    autoplay.current = Autoplay({ delay: 5500, stopOnInteraction: false, stopOnMouseEnter: true });
  }
  const plugins = useRef([autoplay.current]);

  const byKey = Object.fromEntries((plans || []).map((p) => [p.key, p]));

  return (
    <div data-testid="dashboard-plan-carousel">
      <Carousel
        opts={{ align: "center", loop: true, watchDrag: false, duration: 55 }}
        plugins={plugins.current}
      >
        <CarouselContent className="py-8">
          {ORDER.map((key) => {
            const plan = byKey[key];
            if (!plan) return null;
            return (
              <CarouselItem
                key={key}
                data-testid={`dash-carousel-${key}`}
                data-unlocked={plan.unlocked ? "true" : "false"}
                className="basis-auto shrink-0 grow-0 flex flex-col items-center px-4"
              >
                {/* 3D certificate card (same component as the landing carousel) */}
                <div className="relative w-[420px] max-w-[82vw]">
                  <InvestmentCard variant={key} className="mx-auto" />

                  {!plan.unlocked && (
                    <button
                      onClick={() => setBuyPlan(plan)}
                      data-testid={`dash-plan-unlock-${key}`}
                      className="absolute inset-0 z-20 flex flex-col items-center justify-center gap-2 rounded-[28px] bg-black/25 backdrop-blur-[3px] transition hover:bg-black/35"
                    >
                      <Lock className="h-12 w-12 text-yellow-400" strokeWidth={2.25} />
                      <span className="ex-display text-base font-semibold text-white">Tap to unlock</span>
                      <span className="text-xs text-white/70">Invest to reveal this plan</span>
                    </button>
                  )}
                </div>

                {/* Real plan action bar */}
                <div className="mt-4 w-[420px] max-w-[82vw] ex-surface-sm p-3 flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="ex-eyebrow truncate">{plan.name}</span>
                    <EasyXStatusBadge status={plan.unlocked ? "unlocked" : "locked"} />
                    {plan.unlocked && (
                      <span className="text-xs text-ex-muted whitespace-nowrap">· {plan.cards} card{plan.cards === 1 ? "" : "s"}</span>
                    )}
                  </div>
                  {plan.unlocked ? (
                    <div className="flex gap-2 shrink-0">
                      <EasyXButton variant="ghost" className="h-9 px-3" onClick={() => setBuyPlan(plan)} data-testid={`dash-buymore-${key}`}>
                        <Plus className="h-4 w-4" />
                      </EasyXButton>
                      <EasyXButton className="h-9 px-3" onClick={() => navigate(`/app/investments?plan=${key}`)} data-testid={`dash-view-${key}`}>
                        View <ArrowRight className="ml-1 h-4 w-4" />
                      </EasyXButton>
                    </div>
                  ) : (
                    <EasyXButton className="h-9 px-4 shrink-0" onClick={() => setBuyPlan(plan)} data-testid={`dash-buy-${key}`}>
                      Buy {money(plan.price)}
                    </EasyXButton>
                  )}
                </div>
              </CarouselItem>
            );
          })}
        </CarouselContent>
        <CarouselPrevious className="hidden sm:flex" />
        <CarouselNext className="hidden sm:flex" />
      </Carousel>

      {buyPlan && (
        <BuyPlanDialog
          plan={buyPlan}
          open={!!buyPlan}
          onOpenChange={(o) => !o && setBuyPlan(null)}
          walletBalance={walletBalance}
        />
      )}
    </div>
  );
}
