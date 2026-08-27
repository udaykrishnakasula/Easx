import React, { createContext, useContext, useEffect, useMemo } from "react";
import { useLocation } from "react-router-dom";
import { useAuth } from "@/shared/context/AuthContext";
import errorTracker from "./errorTracker";
import behaviourTracker from "./behaviourTracker";
import {
  initPostHog,
  identifyUserInPostHog,
  resetPostHogSession,
  capturePostHogEvent,
  capturePostHogPageView,
} from "./posthog";
import api from "@/shared/lib/api";

const AnalyticsContext = createContext(null);

export function AnalyticsProvider({ children }) {
  const location = useLocation();
  const auth = useAuth();
  const user = auth?.user;

  // 1. Initialize Error, Behaviour Trackers, and PostHog once on mount
  useEffect(() => {
    errorTracker.init();
    behaviourTracker.init();
    initPostHog();

    // Hook into axios interceptor for API errors without mutating existing interceptors
    const responseInterceptor = api.interceptors.response.use(
      (response) => response,
      (error) => {
        try {
          errorTracker.captureApiError(error);
        } catch {
          // ignore tracking error
        }
        return Promise.reject(error);
      }
    );

    return () => {
      api.interceptors.response.eject(responseInterceptor);
    };
  }, []);

  // 2. Sync active user context whenever Auth state changes
  useEffect(() => {
    errorTracker.setUserContext(user);
    behaviourTracker.setUserContext(user);
    if (user) {
      identifyUserInPostHog(user);
    } else {
      resetPostHogSession();
    }
  }, [user]);

  // 3. Track route changes and screen view durations
  useEffect(() => {
    if (location?.pathname) {
      behaviourTracker.handleRouteChange(location.pathname);
      capturePostHogPageView(location.pathname);
    }
  }, [location.pathname]);

  const value = useMemo(
    () => ({
      trackEvent: (category, action, data) => {
        behaviourTracker.recordEvent({ category, action, metadata: data });
        capturePostHogEvent(`${category}:${action}`, data);
      },
      trackFriction: (type, element, text, meta) => {
        behaviourTracker.trackFrictionEvent({
          type,
          element,
          elementText: text,
          metadata: meta,
        });
        capturePostHogEvent(`friction:${type}`, { element, elementText: text, ...meta });
      },
      startFunnel: (name, step, meta) => {
        behaviourTracker.startFunnel(name, step, meta);
        capturePostHogEvent(`funnel_started:${name}`, { step, ...meta });
      },
      stepFunnel: (name, step, meta) => {
        behaviourTracker.stepFunnel(name, step, meta);
        capturePostHogEvent(`funnel_step:${name}`, { step, ...meta });
      },
      completeFunnel: (name, meta) => {
        behaviourTracker.completeFunnel(name, meta);
        capturePostHogEvent(`funnel_completed:${name}`, meta);
      },
      abandonFunnel: (name, reason, meta) => {
        behaviourTracker.abandonFunnel(name, reason, meta);
        capturePostHogEvent(`funnel_abandoned:${name}`, { reason, ...meta });
      },
      captureError: (err, meta) => {
        errorTracker.captureError({ ...meta, message: err?.message || String(err) });
        capturePostHogEvent("$exception", {
          $exception_message: err?.message || String(err),
          $exception_type: err?.name || "Error",
          ...meta,
        });
      },
      getStoredErrors: () => errorTracker.getStoredErrors(),
      getStoredEvents: () => behaviourTracker.getStoredEvents(),
      clearErrors: () => errorTracker.clearLocalErrors(),
      clearEvents: () => behaviourTracker.clearLocalEvents(),
    }),
    []
  );

  return <AnalyticsContext.Provider value={value}>{children}</AnalyticsContext.Provider>;
}

export function useAnalytics() {
  const context = useContext(AnalyticsContext);
  if (!context) {
    // Fallback safe stubs if accessed outside provider
    return {
      trackEvent: () => {},
      trackFriction: () => {},
      startFunnel: () => {},
      stepFunnel: () => {},
      completeFunnel: () => {},
      abandonFunnel: () => {},
      captureError: () => {},
      getStoredErrors: () => [],
      getStoredEvents: () => [],
      clearErrors: () => {},
      clearEvents: () => {},
    };
  }
  return context;
}

export default AnalyticsProvider;
