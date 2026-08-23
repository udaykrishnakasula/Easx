import React, { useRef, useState, useEffect, useCallback } from "react";
import Autoplay from "embla-carousel-autoplay";
import { Lock, ArrowRight, Plus } from "lucide-react";
import { useNavigate } from "react-router-dom";

import {
  Carousel,
  CarouselContent,
  CarouselItem,
} from "@/shared/ui/carousel";
import { InvestmentCard } from "@/components/landing/DiamondInvestmentCard";
import { EasyXButton, EasyXStatusBadge } from "@/design/EasyX";
import BuyPlanDialog from "./BuyPlanDialog";
import { money } from "@/user/api";

const ORDER = ["silver", "gold", "platinum", "diamond"];

export default function DashboardPlanCarousel({ plans, walletBalance, userName }) {
  const navigate = useNavigate();
  const [buyPlan, setBuyPlan] = useState(null);
  const [api, setApi] = useState(null);
  const [selectedIndex, setSelectedIndex] = useState(0);

  const isInteracting = useRef(false);
  const resumeTimer = useRef(null);

  const autoplay = useRef(null);
  if (!autoplay.current) {
    autoplay.current = Autoplay({
      delay: 5500,
      stopOnInteraction: false,
      stopOnMouseEnter: false,
    });
  }
  const plugins = useRef([autoplay.current]);

  const pauseAutoplay = useCallback(() => {
    if (resumeTimer.current) {
      clearTimeout(resumeTimer.current);
      resumeTimer.current = null;
    }
    const ap = api?.plugins()?.autoplay || autoplay.current;
    if (ap && typeof ap.stop === "function") {
      ap.stop();
    }
  }, [api]);

  const resumeAutoplayAfterDelay = useCallback((delayMs = 2000) => {
    if (resumeTimer.current) {
      clearTimeout(resumeTimer.current);
    }
    resumeTimer.current = setTimeout(() => {
      if (!isInteracting.current && !buyPlan) {
        const ap = api?.plugins()?.autoplay || autoplay.current;
        if (ap && typeof ap.play === "function") {
          ap.play();
        }
      }
    }, delayMs);
  }, [api, buyPlan]);

  const handleInteractionStart = useCallback(() => {
    isInteracting.current = true;
    pauseAutoplay();
  }, [pauseAutoplay]);

  const handleInteractionEnd = useCallback(() => {
    isInteracting.current = false;
    resumeAutoplayAfterDelay(2000);
  }, [resumeAutoplayAfterDelay]);

  // Sync with Embla API events
  useEffect(() => {
    if (!api) return;

    const onSelect = () => {
      setSelectedIndex(api.selectedScrollSnap());
    };

    const onPointerDown = () => {
      isInteracting.current = true;
      pauseAutoplay();
    };

    const onPointerUp = () => {
      isInteracting.current = false;
      resumeAutoplayAfterDelay(2000);
    };

    const onScroll = () => {
      if (isInteracting.current) {
        pauseAutoplay();
      }
    };

    onSelect();
    api.on("select", onSelect);
    api.on("reInit", onSelect);
    api.on("pointerDown", onPointerDown);
    api.on("pointerUp", onPointerUp);
    api.on("scroll", onScroll);

    return () => {
      api.off("select", onSelect);
      api.off("reInit", onSelect);
      api.off("pointerDown", onPointerDown);
      api.off("pointerUp", onPointerUp);
      api.off("scroll", onScroll);
      if (resumeTimer.current) {
        clearTimeout(resumeTimer.current);
      }
    };
  }, [api, pauseAutoplay, resumeAutoplayAfterDelay]);

  // Pause when buy dialog is open
  useEffect(() => {
    if (buyPlan) {
      pauseAutoplay();
    } else {
      resumeAutoplayAfterDelay(2000);
    }
  }, [buyPlan, pauseAutoplay, resumeAutoplayAfterDelay]);

  const byKey = Object.fromEntries((plans || []).map((p) => [p.key, p]));

  return (
    <div
      data-testid="dashboard-plan-carousel"
      className="relative select-none group"
      onMouseEnter={handleInteractionStart}
      onMouseLeave={handleInteractionEnd}
      onTouchStart={handleInteractionStart}
      onTouchEnd={handleInteractionEnd}
      onTouchCancel={handleInteractionEnd}
      onPointerDown={handleInteractionStart}
      onPointerUp={handleInteractionEnd}
      onPointerCancel={handleInteractionEnd}
    >
      <Carousel
        setApi={setApi}
        opts={{ align: "center", loop: true, skipSnaps: false, duration: 40 }}
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
                  <InvestmentCard
                    variant={key}
                    plan={plan}
                    investment={plan.latest_investment}
                    userName={userName}
                    className="mx-auto"
                  />

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
      </Carousel>

      {/* Slide dots indicator */}
      <div className="flex items-center justify-center gap-2 mt-1 pb-2">
        {ORDER.map((key, idx) => (
          <button
            key={key}
            type="button"
            onClick={() => {
              pauseAutoplay();
              api?.scrollTo(idx);
              resumeAutoplayAfterDelay(2000);
            }}
            aria-label={`Go to ${key} plan`}
            className={`h-1.5 rounded-full transition-all duration-300 ${
              selectedIndex === idx
                ? "w-6 bg-gradient-to-r from-violet-400 to-indigo-400 shadow-sm shadow-violet-500/50"
                : "w-1.5 bg-white/20 hover:bg-white/40"
            }`}
          />
        ))}
      </div>

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
