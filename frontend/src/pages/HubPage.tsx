import { SourcePreviewCard } from "@/components/cards/SourcePreviewCard";
import { currentUser, sources } from "@/data/mockData";

export function HubPage() {
  const topPick = sources[0]!;
  const digestSources = sources.slice(1, 5);

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900">Welcome back {currentUser.name}!</h1>
      <p className="mt-1 text-sm text-gray-600">
        Here are the top 5 papers that matched your recent research!
      </p>

      <section className="mt-8">
        <h2 className="mb-4 text-sm font-semibold tracking-wide text-gray-500">
          TOP PICK THIS WEEK
        </h2>
        <SourcePreviewCard source={topPick} sourceReferrer={{ type: "hub" }} variant="featured" />
      </section>

      <section className="mt-10">
        <h2 className="mb-4 text-sm font-semibold tracking-wide text-gray-500">
          MORE FROM YOUR DIGEST
        </h2>
        <div className="grid grid-cols-2 gap-4">
          {digestSources.map((source) => (
            <SourcePreviewCard
              key={source.id}
              source={source}
              sourceReferrer={{ type: "hub" }}
              variant="compact"
            />
          ))}
        </div>
      </section>
    </div>
  );
}
