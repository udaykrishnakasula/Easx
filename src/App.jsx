import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import Hero from "@/components/landing/Hero";
import Sections from "@/components/landing/Sections";
import { AuthProvider } from "@/shared/context/AuthContext";
import { ProtectedRoute } from "@/shared/components/ProtectedRoute";
import LoginPage from "@/shared/auth/LoginPage";
import RegisterPage from "@/shared/auth/RegisterPage";
import UserRoutes from "@/user/routes/UserRoutes";
import AdminRoutes from "@/admin/routes/AdminRoutes";

const Landing = () => (
  <main data-testid="landing-page">
    <Hero />
    <Sections />
  </main>
);

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            {/* Public Landing & Authentication */}
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

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
          <Toaster position="top-center" richColors />
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
