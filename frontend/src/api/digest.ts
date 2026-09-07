import { getProfile } from "@/api/profile";
import { listProjects } from "@/api/projects";
import { searchSources } from "@/api/research";
import { listSavedSources } from "@/api/sources";
import { cacheSources } from "@/api/mappers";
import { mockStore } from "@/api/mocks/store";
import { env } from "@/config/env";
import type { Project, Source, UserProfile } from "@/types";

export interface HubDigest {
  topPick: Source | null;
  items: Source[];
  /** Interest terms used to build the digest query. */
  interests: string[];
  /** ISO timestamp when this digest was generated. */
  generatedAt: string;
}

const DIGEST_SIZE = 5;
const MAX_QUERY_TERMS = 10;
const MAX_SEARCH_QUERIES = 4;
const DIGEST_CACHE_KEY = "papersearcher_hub_digest_v2";

interface DigestCachePayload {
  generatedAt: string;
  interests: string[];
  digest: HubDigest;
}

function uniqueTerms(values: string[]): string[] {
  const seen = new Set<string>();
  const terms: string[] = [];
  for (const raw of values) {
    const term = raw.trim();
    if (!term) continue;
    const key = term.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    terms.push(term);
  }
  return terms;
}

/** Most recent Monday 08:00 local time at or before `now`. */
function lastMonday8am(now = new Date()): Date {
  const d = new Date(now);
  const day = d.getDay(); // 0 Sun … 1 Mon
  const daysSinceMonday = (day + 6) % 7;
  d.setDate(d.getDate() - daysSinceMonday);
  d.setHours(8, 0, 0, 0);
  if (now < d) {
    d.setDate(d.getDate() - 7);
  }
  return d;
}

function interestsEqual(a: string[], b: string[]): boolean {
  if (a.length !== b.length) return false;
  const left = a.map((t) => t.toLowerCase()).sort();
  const right = b.map((t) => t.toLowerCase()).sort();
  return left.every((term, i) => term === right[i]);
}

function rehydrateDigestSources(digest: HubDigest): HubDigest {
  const sources = [digest.topPick, ...digest.items].filter(
    (source): source is Source => source != null,
  );
  cacheSources(sources);
  return digest;
}

function readDigestCache(): DigestCachePayload | null {
  try {
    const raw = localStorage.getItem(DIGEST_CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as DigestCachePayload;
    if (!parsed?.digest || !parsed.generatedAt || !Array.isArray(parsed.interests)) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

function writeDigestCache(digest: HubDigest): void {
  rehydrateDigestSources(digest);
  const payload: DigestCachePayload = {
    generatedAt: digest.generatedAt,
    interests: digest.interests,
    digest,
  };
  localStorage.setItem(DIGEST_CACHE_KEY, JSON.stringify(payload));
}

/** Profile onboarding interests first, then current project topics/keywords. */
function collectDigestInterests(
  profile: UserProfile,
  projects: Project[],
): string[] {
  const profileTerms = uniqueTerms([
    ...profile.researchAreas,
    ...profile.keywords,
  ]);
  const projectTerms = uniqueTerms(
    projects.flatMap((project) => [...project.topics, ...project.keywords]),
  );
  return uniqueTerms([...profileTerms, ...projectTerms]).slice(0, MAX_QUERY_TERMS);
}

function sourceKey(source: Source): string {
  return (source.externalId ?? source.id).toLowerCase();
}

function scoreSource(source: Source, interests: string[]): number {
  if (source.similarity != null) return source.similarity;
  if (source.relevance != null) return source.relevance;
  const haystack = [
    source.title,
    source.description,
    ...source.topics,
    ...source.relevantTo,
  ]
    .join(" ")
    .toLowerCase();
  let hits = 0;
  for (const interest of interests) {
    const term = interest.toLowerCase();
    if (haystack.includes(term)) hits += 2;
    // Partial tokens help for labels like "AI/ML"
    for (const part of term.split(/[^a-z0-9]+/).filter((p) => p.length > 1)) {
      if (haystack.includes(part)) hits += 1;
    }
  }
  return hits;
}

function rankAndDedupe(sources: Source[], interests: string[]): Source[] {
  const best = new Map<string, Source>();
  for (const source of sources) {
    const key = sourceKey(source);
    const existing = best.get(key);
    if (!existing || scoreSource(source, interests) > scoreSource(existing, interests)) {
      best.set(key, source);
    }
  }
  return [...best.values()].sort(
    (a, b) => scoreSource(b, interests) - scoreSource(a, interests),
  );
}

function filterByInterests(sources: Source[], interests: string[]): Source[] {
  if (interests.length === 0) return sources;
  const matched = sources.filter((source) => scoreSource(source, interests) > 0);
  return matched.length > 0 ? matched : sources;
}

async function collectSavedIds(projects: Project[]): Promise<Set<string>> {
  const ids = new Set<string>();
  await Promise.all(
    projects.map(async (project) => {
      const saved = await listSavedSources(project.id).catch(() => [] as Source[]);
      for (const source of saved) {
        ids.add(sourceKey(source));
        ids.add(source.id.toLowerCase());
      }
    }),
  );
  return ids;
}

function toDigest(sources: Source[], interests: string[]): HubDigest {
  const [topPick = null, ...rest] = sources.slice(0, DIGEST_SIZE);
  return {
    topPick,
    items: rest,
    interests,
    generatedAt: new Date().toISOString(),
  };
}

async function fetchDigestPapers(
  interests: string[],
  savedIds: Set<string>,
): Promise<Source[]> {
  const queries = interests.slice(0, MAX_SEARCH_QUERIES);

  // Try discovery per interest first (no legacy — avoids N× slow provider fan-out).
  const discoveryBatches = await Promise.all(
    queries.map((q) =>
      searchSources(q, { fallbackToLegacy: false }).catch(() => [] as Source[]),
    ),
  );
  let ranked = rankAndDedupe(discoveryBatches.flat(), interests).filter(
    (source) => !savedIds.has(sourceKey(source)) && !savedIds.has(source.id.toLowerCase()),
  );

  // One legacy provider search if discovery is down (e.g. Voyage auth).
  if (ranked.length === 0 && queries.length > 0) {
    const fallback = await searchSources(queries[0]!).catch(
      () => [] as Source[],
    );
    ranked = rankAndDedupe(fallback, interests).filter(
      (source) => !savedIds.has(sourceKey(source)) && !savedIds.has(source.id.toLowerCase()),
    );
  }

  return ranked;
}

/**
 * Hub recommendations from profile topics/keywords plus current project interests.
 *
 * - Populates on first visit (no cache).
 * - Refreshes every Monday at 8:00 local time, or when interests change.
 */
export async function getHubDigest(options?: { force?: boolean }): Promise<HubDigest> {
  const [profile, projects] = await Promise.all([getProfile(), listProjects()]);
  const interests = collectDigestInterests(profile, projects);

  if (interests.length === 0) {
    return {
      topPick: null,
      items: [],
      interests: [],
      generatedAt: new Date().toISOString(),
    };
  }

  if (!options?.force) {
    const cached = readDigestCache();
    if (
      cached &&
      interestsEqual(cached.interests, interests) &&
      new Date(cached.generatedAt) >= lastMonday8am()
    ) {
      return rehydrateDigestSources({
        ...cached.digest,
        interests,
      });
    }
  }

  const savedIds = await collectSavedIds(projects);

  if (env.useMocks) {
    const ranked = rankAndDedupe(
      filterByInterests(mockStore.sources, interests),
      interests,
    ).filter(
      (source) => !savedIds.has(sourceKey(source)) && !savedIds.has(source.id.toLowerCase()),
    );
    const digest = toDigest(ranked, interests);
    writeDigestCache(digest);
    return digest;
  }

  const ranked = await fetchDigestPapers(interests, savedIds);
  const digest = toDigest(ranked, interests);
  if (digest.topPick) {
    writeDigestCache(digest);
  }
  return digest;
}
