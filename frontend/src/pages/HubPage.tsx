import { useEffect, useState } from "react";

import { getHubDigest, type HubDigest } from "@/api/digest";
import { getProfile } from "@/api/profile";
import { SourcePreviewCard } from "@/components/cards/SourcePreviewCard";
import type { UserProfile } from "@/types";

export function HubPage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [digest, setDigest] = useState<HubDigest | null>(null);

  useEffect(() => {
    void getProfile().then(setProfile);
    void getHubDigest().then(setDigest);
  }, []);

  if (!profile || !digest) {
    return <p className="text-sm text-gray-500">Loading…</p>;
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900">Welcome back {profile.name}!</h1>
      <p className="mt-1 text-sm text-gray-600">
        Here are the top 5 papers that matched your recent research!
      </p>

      <section className="mt-8">
        <h2 className="mb-4 text-sm font-semibold tracking-wide text-gray-500">
          TOP PICK THIS WEEK
        </h2>
        {digest.topPick ? (
          <SourcePreviewCard
            source={digest.topPick}
            sourceReferrer={{ type: "hub" }}
            variant="featured"
          />
        ) : (
          <p className="rounded-xl border border-dashed border-gray-200 bg-white p-6 text-sm text-gray-500">
            No digest recommendations yet.
          </p>
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
                sourceReferrer={{ type: "hub" }}
                variant="compact"
              />
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-500">No additional digest papers yet.</p>
        )}
      </section>
    </div>
  );
}
