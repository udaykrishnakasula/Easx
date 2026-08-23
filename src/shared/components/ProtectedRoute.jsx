import React, { useEffect, useRef } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { toast } from "sonner";
import { useAuth } from "@/shared/context/AuthContext";

function FullScreenLoader() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0d0b14]">
      <div className="h-8 w-8 rounded-full border-2 border-white/20 border-t-white animate-spin" />
    </div>
  );
}

export function ProtectedRoute({ children, adminOnly = false }) {
  const { user, loading, isAdmin } = useAuth();
  const location = useLocation();
  const warnedRef = useRef(false);

  useEffect(() => {
    if (!loading && user && adminOnly && !isAdmin && !warnedRef.current) {
      warnedRef.current = true;
      toast.error("403 Forbidden: Admin privileges required. Redirected to User Dashboard.");
    }
  }, [loading, user, adminOnly, isAdmin]);

  if (loading) return <FullScreenLoader />;
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  if (adminOnly && !isAdmin) return <Navigate to="/dashboard" replace />;
  return children;
}

export default ProtectedRoute;
