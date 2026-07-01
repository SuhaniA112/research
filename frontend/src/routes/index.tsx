import { Navigate, Outlet, Route, Routes } from "react-router-dom";

import { getAccessToken } from "@/lib/axios";
import { LoginPage } from "@/pages/LoginPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { HubPage } from "@/pages/HubPage";
import { AllProjectsPage } from "@/pages/AllProjectsPage";
import { OnboardingPage } from "@/pages/OnboardingPage";
import { ProfilePage } from "@/pages/ProfilePage";
import { RecentSearchesPage } from "@/pages/RecentSearchesPage";
import { ProjectOverviewPage } from "@/pages/project/ProjectOverviewPage";
import { SavedSourcesPage } from "@/pages/project/SavedSourcesPage";
import { MindMapPage } from "@/pages/project/MindMapPage";
import { FindSourcesPage } from "@/pages/project/FindSourcesPage";
import { SourceDetailPage } from "@/pages/project/SourceDetailPage";
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
          <Route path="/dashboard" element={<Navigate to="/hub" replace />} />
          <Route path="/hub" element={<HubPage />} />
          <Route path="/projects" element={<AllProjectsPage />} />
          <Route path="/onboarding" element={<OnboardingPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/searches" element={<RecentSearchesPage />} />

          <Route path="/projects/:projectId" element={<ProjectOverviewPage />} />
          <Route path="/projects/:projectId/saved" element={<SavedSourcesPage />} />
          <Route path="/projects/:projectId/mind-map" element={<MindMapPage />} />
          <Route path="/projects/:projectId/find-sources" element={<FindSourcesPage />} />
          <Route path="/projects/:projectId/sources/:sourceId" element={<SourceDetailPage />} />
        </Route>
      </Route>

      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
