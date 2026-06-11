import { Navigate, Outlet, Route, Routes } from "react-router-dom";

import { getAccessToken } from "@/lib/axios";
import { DashboardPage } from "@/pages/DashboardPage";
import { LoginPage } from "@/pages/LoginPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { PublicLayout } from "@/layouts/PublicLayout";
import { ProtectedLayout } from "@/layouts/ProtectedLayout";

function RequireAuth() {
  const token = getAccessToken();
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <Outlet />;
}

function RedirectIfAuthenticated() {
  const token = getAccessToken();
  if (token) {
    return <Navigate to="/dashboard" replace />;
  }
  return <Outlet />;
}

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route element={<RedirectIfAuthenticated />}>
          <Route path="/login" element={<LoginPage />} />
        </Route>
      </Route>

      <Route element={<RequireAuth />}>
        <Route element={<ProtectedLayout />}>
          <Route path="/dashboard" element={<DashboardPage />} />
        </Route>
      </Route>

      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
