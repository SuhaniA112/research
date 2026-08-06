import { useEffect, useState } from "react";

import { ensureSourceSummaries } from "@/api/sources";
import { hasLeveledSummaries } from "@/lib/summaries";
import type { Source } from "@/types";

/**
 * Lazily generate/fetch leveled summaries + key findings for any source card/page.
 * Dedupes in-flight requests in ensureSourceSummaries.
 */
export function useHydratedSource(source: Source): {
  source: Source;
  summarizing: boolean;
} {
  const [hydrated, setHydrated] = useState(source);
  const [summarizing, setSummarizing] = useState(false);

  useEffect(() => {
    setHydrated(source);
    if (hasLeveledSummaries(source)) {
      setSummarizing(false);
      return;
    }

    let cancelled = false;
    setSummarizing(true);
    void ensureSourceSummaries(source)
      .then((next) => {
        if (!cancelled) setHydrated(next);
      })
      .finally(() => {
        if (!cancelled) setSummarizing(false);
      });

    return () => {
      cancelled = true;
    };
  }, [
    source.id,
    source.externalId,
    source.summaries?.general,
    source.summaries?.graduate,
    source.summaries?.expert,
    source.description,
    source.title,
  ]);

  return { source: hydrated, summarizing };
}
