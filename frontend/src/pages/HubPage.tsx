import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { getHubDigest } from "@/api/digest";
import { getProfile } from "@/api/profile";
import { listProjects } from "@/api/projects";
import {
  fetchDigestPage,
  readDigestSnapshot,
  scoreForProject,
  writeDigestSnapshot,
  type DigestPage,
} from "@/api/recommendations";
import { searchSources } from "@/api/research";
import { SourcePreviewCard } from "@/components/cards/SourcePreviewCard";
import { env } from "@/config/env";
import type { Source, UserProfile } from "@/types";

const FIRST_PAGE = 5;
const MORE_PAGE = 4;

/** Mock mode keeps the original client-side digest. */
async function loadMockDigest(): Promise<DigestPage> {
  const digest = await getHubDigest();
  const items = [digest.topPick, ...digest.items].filter((s): s is Source => s != null);
  return {
    interests: digest.interests,
    items,
    total: items.length,
    hasMore: false,
    sparse: false,
    method: "lexical",
    generatedAt: digest.generatedAt,
  };
}

function CardSkeleton({ tall = false }: { tall?: boolean }) {
  return (
    <div
      className={`animate-pulse rounded-xl border border-gray-200 bg-white p-5 ${tall ? "h-48" : "h-36"}`}
    >
      <div className="h-3 w-1/3 rounded bg-gray-100" />
      <div className="mt-3 h-4 w-3/4 rounded bg-gray-100" />
      <div className="mt-2 h-3 w-full rounded bg-gray-100" />
      <div className="mt-2 h-3 w-5/6 rounded bg-gray-100" />
    </div>
  );
}

export function HubPage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  // Paint the last digest immediately, then refresh in the background.
  const [digest, setDigest] = useState<DigestPage | null>(() =>
    env.useMocks ? null : readDigestSnapshot(),
  );
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [projectId, setProjectId] = useState<string | undefined>(undefined);
  const [projectName, setProjectName] = useState<string | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);
  const enriched = useRef(false);

  const refresh = useCallback(async (force = false) => {
    const load = () =>
      env.useMocks ? loadMockDigest() : fetchDigestPage({ limit: FIRST_PAGE, refresh: force });
    // One retry covers a brand-new user's first request racing account setup.
    const page = await load().catch(() => load());
    setDigest(page);
    if (!env.useMocks && page.items.length > 0) writeDigestSnapshot(page);
    return page;
  }, []);

  useEffect(() => {
    let cancelled = false;
    void getProfile().then((p) => !cancelled && setProfile(p)).catch(() => undefined);
    void listProjects()
      .then((projects) => {
        if (cancelled) return;
        setProjectId(projects[0]?.id);
        setProjectName(projects[0]?.name);
      })
      .catch(() => undefined);

    void refresh()
      .then(async (page) => {
        // Few stored matches: run one live search to grow the pool, then re-rank.
        if (cancelled || env.useMocks || !page.sparse || enriched.current) return;
        const interest = page.interests[0];
        if (!interest) return;
        enriched.current = true;
        await searchSources(interest, { fallbackToLegacy: false }).catch(() => []);
        if (cancelled) return;
        const next = await refresh(true);
        if (cancelled || next.method === "embedding") return;
        // Still no stored match: show live results for a few interests directly.
        const batches = await Promise.all(
          next.interests.slice(0, 3).map((q) => searchSources(q).catch(() => [] as Source[])),
        );
        const seen = new Set<string>();
        const live = batches
          .flat()
          .filter((s) => !seen.has(s.id) && seen.add(s.id))
          .sort((a, b) => (b.relevance ?? 0) - (a.relevance ?? 0))
          .slice(0, FIRST_PAGE + MORE_PAGE);
        if (!cancelled && live.length > 0) {
          setDigest({ ...next, items: live, total: live.length, hasMore: false, method: "live" });
        }
      })
      .catch(() => {
        if (!cancelled) setError("Couldn't load recommendations. Refresh the page to try again.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [refresh]);

  // Card scores are relative to the most recent project, like everywhere else.
  const itemIds = digest?.items.map((s) => s.id).join(",") ?? "";
  useEffect(() => {
    if (env.useMocks || !projectId || !digest?.items.length) return;
    let cancelled = false;
    void scoreForProject(projectId, digest.items)
      .then((scored) => {
        if (cancelled) return;
        setDigest((d) =>
          d && d.items.map((s) => s.id).join(",") === itemIds ? { ...d, items: scored } : d,
        );
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, itemIds]);

  async function loadMore() {
    if (!digest) return;
    setLoadingMore(true);
    try {
      const next = await fetchDigestPage({ offset: digest.items.length, limit: MORE_PAGE });
      setDigest({ ...digest, items: [...digest.items, ...next.items], hasMore: next.hasMore });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load more papers");
    } finally {
      setLoadingMore(false);
    }
  }

  const interests = digest?.interests ?? profile?.researchAreas ?? [];
  const hasInterests = interests.length > 0;
  const [topPick, ...rest] = digest?.items ?? [];
  const showSkeletons = !digest && loading;
  const hubReferrer = { type: "hub" as const, projectId };

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900">
        Welcome back{profile ? ` ${profile.name}` : ""}!
      </h1>
      <p className="mt-1 text-sm text-gray-600">
        {hasInterests || showSkeletons
          ? "Here are top papers matched to your profile interests and current projects."
          : "Add research areas on your profile or create a project to personalize your digest."}
      </p>
      {hasInterests ? (
        <p className="mt-2 text-xs text-gray-500">
          Based on: {interests.slice(0, 8).join(" · ")}
          {interests.length > 8 ? "…" : ""}
          {loading && digest ? " · Updating…" : ""}
        </p>
      ) : null}

      {projectName && digest?.items.length ? (
        <p className="mt-1 text-xs text-gray-500">
          Relevance and similarity are scored for your project &ldquo;{projectName}&rdquo;.
        </p>
      ) : null}
      {digest?.method === "recent" ? (
        <p className="mt-2 text-xs text-gray-500">
          {hasInterests
            ? "No close matches for your interests yet, so these are recently added papers."
            : "Showing recently added papers. "}
          {!hasInterests ? (
            <Link to="/profile" className="font-medium text-brand-700 hover:underline">
              Add research areas to personalize.
            </Link>
          ) : null}
        </p>
      ) : digest?.method === "embedding" && !hasInterests ? (
        <p className="mt-2 text-xs text-gray-500">
          Based on papers you&apos;ve saved.{" "}
          <Link to="/profile" className="font-medium text-brand-700 hover:underline">
            Add research areas
          </Link>{" "}
          to personalize further.
        </p>
      ) : digest?.method === "live" ? (
        <p className="mt-2 text-xs text-gray-500">Fresh results from a live search of your interests.</p>
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
        {topPick ? (
          <SourcePreviewCard
            source={topPick}
            projectId={projectId}
            sourceReferrer={hubReferrer}
            variant="featured"
          />
        ) : showSkeletons ? (
          <CardSkeleton tall />
        ) : (
          <div className="rounded-xl border border-dashed border-gray-200 bg-white p-6 text-sm text-gray-500">
            {hasInterests ? (
              <p>
                {loading
                  ? "Searching for papers that match your interests…"
                  : "No matching papers yet. Save a few papers to a project, or search from a project, and recommendations will appear here."}
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
        {rest.length > 0 ? (
          <div className="grid grid-cols-2 gap-4">
            {rest.map((source) => (
              <SourcePreviewCard
                key={source.id}
                source={source}
                projectId={projectId}
                sourceReferrer={hubReferrer}
                variant="compact"
              />
            ))}
          </div>
        ) : showSkeletons ? (
          <div className="grid grid-cols-2 gap-4">
            {[0, 1, 2, 3].map((i) => (
              <CardSkeleton key={i} />
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-500">
            {topPick ? "No additional digest papers yet." : "Additional matches will show up here."}
          </p>
        )}
        {digest?.hasMore ? (
          <button
            type="button"
            onClick={() => void loadMore()}
            disabled={loadingMore}
            className="mt-6 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-60"
          >
            {loadingMore ? "Loading…" : "Load more"}
          </button>
        ) : null}
      </section>
    </div>
  );
}
