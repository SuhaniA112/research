import { lazy, Suspense } from "react";
import { Navigate, Outlet, Route, Routes } from "react-router-dom";

import { getAccessToken } from "@/lib/axios";
import { isOnboardingComplete } from "@/lib/onboarding";
import { LoginPage } from "@/pages/LoginPage";
import { PublicLayout } from "@/layouts/PublicLayout";

// Everything past login is code-split so the login screen loads a small bundle.
const named = <T extends string>(load: () => Promise<Record<T, React.ComponentType>>, name: T) =>
  lazy(() => load().then((m) => ({ default: m[name] })));

const NotFoundPage = named(() => import("@/pages/NotFoundPage"), "NotFoundPage");
const HubPage = named(() => import("@/pages/HubPage"), "HubPage");
const AllProjectsPage = named(() => import("@/pages/AllProjectsPage"), "AllProjectsPage");
const NewProjectPage = named(() => import("@/pages/NewProjectPage"), "NewProjectPage");
const OnboardingPage = named(() => import("@/pages/OnboardingPage"), "OnboardingPage");
const ProfilePage = named(() => import("@/pages/ProfilePage"), "ProfilePage");
const RecentSearchesPage = named(() => import("@/pages/RecentSearchesPage"), "RecentSearchesPage");
const ProjectOverviewPage = named(() => import("@/pages/project/ProjectOverviewPage"), "ProjectOverviewPage");
const SavedSourcesPage = named(() => import("@/pages/project/SavedSourcesPage"), "SavedSourcesPage");
const MindMapPage = named(() => import("@/pages/project/MindMapPage"), "MindMapPage");
const FindSourcesPage = named(() => import("@/pages/project/FindSourcesPage"), "FindSourcesPage");
const SourceDetailPage = named(() => import("@/pages/project/SourceDetailPage"), "SourceDetailPage");
const ProtectedLayout = named(() => import("@/layouts/ProtectedLayout"), "ProtectedLayout");
const OnboardingLayout = named(() => import("@/layouts/OnboardingLayout"), "OnboardingLayout");

/** Warm the post-login chunks while the user is on the login screen. */
export function prefetchAppShell(): void {
  void import("@/layouts/ProtectedLayout");
  void import("@/pages/HubPage");
}

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

function DashboardEntry() {
  if (!isOnboardingComplete()) {
    return <Navigate to="/onboarding" replace />;
  }
  return <Navigate to="/hub" replace />;
}

function RequireOnboardingComplete() {
  if (!isOnboardingComplete()) {
    return <Navigate to="/onboarding" replace />;
  }
  return <Outlet />;
}

function RedirectIfOnboardingComplete() {
  if (isOnboardingComplete()) {
    return <Navigate to="/hub" replace />;
  }
  return <Outlet />;
}

export function AppRoutes() {
  return (
    <Suspense fallback={<p className="p-8 text-sm text-gray-500">Loading…</p>}>
    <Routes>
      <Route element={<PublicLayout />}>
        <Route element={<RedirectIfAuthenticated />}>
          <Route path="/login" element={<LoginPage />} />
        </Route>
      </Route>

      <Route element={<RequireAuth />}>
        <Route path="/dashboard" element={<DashboardEntry />} />

        <Route element={<RedirectIfOnboardingComplete />}>
          <Route element={<OnboardingLayout />}>
            <Route path="/onboarding" element={<OnboardingPage />} />
          </Route>
        </Route>

        <Route element={<RequireOnboardingComplete />}>
          <Route element={<ProtectedLayout />}>
            <Route path="/hub" element={<HubPage />} />
            <Route path="/projects" element={<AllProjectsPage />} />
            <Route path="/projects/new" element={<NewProjectPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/searches" element={<RecentSearchesPage />} />

            <Route path="/projects/:projectId" element={<ProjectOverviewPage />} />
            <Route path="/projects/:projectId/saved" element={<SavedSourcesPage />} />
            <Route path="/projects/:projectId/mind-map" element={<MindMapPage />} />
            <Route path="/projects/:projectId/find-sources" element={<FindSourcesPage />} />
            <Route path="/projects/:projectId/sources/:sourceId" element={<SourceDetailPage />} />
          </Route>
        </Route>
      </Route>

      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
    </Suspense>
  );
}
