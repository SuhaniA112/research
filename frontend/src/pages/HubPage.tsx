import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getHubDigest, type HubDigest } from "@/api/digest";
import { getProfile } from "@/api/profile";
import { listProjects } from "@/api/projects";
import { SourcePreviewCard } from "@/components/cards/SourcePreviewCard";
import type { UserProfile } from "@/types";

export function HubPage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [digest, setDigest] = useState<HubDigest | null>(null);
  const [projectId, setProjectId] = useState<string | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    void Promise.all([getProfile(), getHubDigest(), listProjects()])
      .then(([nextProfile, nextDigest, projects]) => {
        if (cancelled) return;
        setProfile(nextProfile);
        setDigest(nextDigest);
        setProjectId(projects[0]?.id);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Failed to load digest");
        setDigest({
          topPick: null,
          items: [],
          interests: [],
          generatedAt: new Date().toISOString(),
        });
        void getProfile().then((p) => {
          if (!cancelled) setProfile(p);
        });
        void listProjects().then((projects) => {
          if (!cancelled) setProjectId(projects[0]?.id);
        });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!profile || !digest) {
    return <p className="text-sm text-gray-500">Finding papers for your interests…</p>;
  }

  const hasInterests = digest.interests.length > 0;
  const hasResults = Boolean(digest.topPick) || digest.items.length > 0;
  const hubReferrer = { type: "hub" as const, projectId };

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900">Welcome back {profile.name}!</h1>
      <p className="mt-1 text-sm text-gray-600">
        {hasInterests
          ? "Here are top papers matched to your profile interests and current projects."
          : "Add research areas on your profile or create a project to personalize your digest."}
      </p>
      {hasInterests ? (
        <p className="mt-2 text-xs text-gray-500">
          Based on: {digest.interests.slice(0, 8).join(" · ")}
          {digest.interests.length > 8 ? "…" : ""}
          {" · "}Refreshes Mondays at 8:00 AM
        </p>
      ) : null}

      {error ? (
        <p className="mt-4 text-sm text-red-600" role="alert">
          {error}
        </p>
      ) : null}

      <section className="mt-8">
        <h2 className="mb-4 text-sm font-semibold tracking-wide text-gray-500">
          TOP PICK THIS WEEK
        </h2>
        {digest.topPick ? (
          <SourcePreviewCard
            source={digest.topPick}
            projectId={projectId}
            sourceReferrer={hubReferrer}
            variant="featured"
          />
        ) : (
          <div className="rounded-xl border border-dashed border-gray-200 bg-white p-6 text-sm text-gray-500">
            {hasInterests ? (
              <p>
                We couldn&apos;t fetch papers for your interests right now. Refresh the page to
                try again — your weekly digest also refreshes every Monday at 8:00 AM.
              </p>
            ) : (
              <p>
                No interests yet.{" "}
                <Link to="/profile" className="font-medium text-brand-700 hover:underline">
                  Update your profile
                </Link>{" "}
                or{" "}
                <Link to="/projects/new" className="font-medium text-brand-700 hover:underline">
                  create a project
                </Link>
                .
              </p>
            )}
          </div>
        )}
      </section>

      <section className="mt-10">
        <h2 className="mb-4 text-sm font-semibold tracking-wide text-gray-500">
          MORE FROM YOUR DIGEST
        </h2>
        {digest.items.length > 0 ? (
          <div className="grid grid-cols-2 gap-4">
            {digest.items.map((source) => (
              <SourcePreviewCard
                key={source.id}
                source={source}
                projectId={projectId}
                sourceReferrer={hubReferrer}
                variant="compact"
              />
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-500">
            {hasResults
              ? "No additional digest papers yet."
              : "Additional matches will show up here."}
          </p>
        )}
      </section>
    </div>
  );
}
