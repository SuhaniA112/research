import { useEffect, useState } from "react";

import { getProfile } from "@/api/profile";
import type { ReadingLevel } from "@/types";

/** Current profile reading level for card blurbs (defaults to graduate). */
export function useReadingLevel(): ReadingLevel {
  const [level, setLevel] = useState<ReadingLevel>("graduate");

  useEffect(() => {
    let cancelled = false;
    void getProfile().then((profile) => {
      if (!cancelled) setLevel(profile.readingLevel);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return level;
}
