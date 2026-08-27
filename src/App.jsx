import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import AppToaster from "@/shared/components/AppToaster";
import Hero from "@/components/landing/Hero";
import Sections from "@/components/landing/Sections";
import { AuthProvider } from "@/shared/context/AuthContext";
import { ProtectedRoute } from "@/shared/components/ProtectedRoute";
import ErrorBoundary from "@/shared/analytics/ErrorBoundary";
import AnalyticsProvider from "@/shared/analytics/AnalyticsProvider";
import LoginPage from "@/shared/auth/LoginPage";
import RegisterPage from "@/shared/auth/RegisterPage";
import ForgotPasswordPage from "@/shared/auth/ForgotPasswordPage";
import UserRoutes from "@/user/routes/UserRoutes";
import AdminRoutes from "@/admin/routes/AdminRoutes";
import GlobalKeyboardShortcuts from "@/shared/components/GlobalKeyboardShortcuts";

const Landing = () => (
  <main data-testid="landing-page">
    <Hero />
    <Sections />
  </main>
);

function App() {
  return (
    <div className="App">
      <ErrorBoundary>
        <BrowserRouter>
          <AuthProvider>
            <AnalyticsProvider>
              <Routes>
                {/* Public Landing & Authentication */}
                <Route path="/" element={<Landing />} />
                <Route path="/login" element={<LoginPage />} />
                <Route path="/register" element={<RegisterPage />} />
                <Route path="/forgot-password" element={<ForgotPasswordPage />} />
                <Route path="/reset-password" element={<ForgotPasswordPage />} />

                {/* Legacy /app paths backwards-compatibility redirect */}
                <Route path="/app" element={<Navigate to="/dashboard" replace />} />
                <Route path="/app/*" element={<Navigate to="/dashboard" replace />} />

                {/* Admin Application Architecture (/admin/*) */}
                <Route
                  path="/admin/*"
                  element={
                    <ProtectedRoute adminOnly>
                      <AdminRoutes />
                    </ProtectedRoute>
                  }
                />

                {/* User Application Architecture (/dashboard, /investments, /wallet, etc.) */}
                <Route
                  path="/*"
                  element={
                    <ProtectedRoute>
                      <UserRoutes />
                    </ProtectedRoute>
                  }
                />

                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
              <GlobalKeyboardShortcuts />
              <AppToaster />
            </AnalyticsProvider>
          </AuthProvider>
        </BrowserRouter>
      </ErrorBoundary>
    </div>
  );
}

export default App;
