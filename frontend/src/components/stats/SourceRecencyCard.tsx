import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { SourceRecencyStats } from "@/api/stats";
import { ProjectStatCard } from "@/components/stats/ProjectStatCard";

interface SourceRecencyCardProps {
  stats: SourceRecencyStats | null;
}

/** Brand light → brand dark (matches --brand-light / --brand). */
const FILL_LIGHT = { r: 251, g: 207, b: 232 }; // #fbcfe8
const FILL_DARK = { r: 136, g: 45, b: 96 }; // #882d60

function lerp(a: number, b: number, t: number): number {
  return Math.round(a + (b - a) * t);
}

/**
 * Gradient by recency: lightest for earliest years, darkest for current /
 * last 3 calendar years.
 */
export function recencyBarFill(
  year: number,
  startYear: number,
  presentYear: number,
): string {
  const recentStart = presentYear - 2;
  let t: number;

  if (year >= recentStart) {
    // Last 3 years sit on the dark end of the scale
    t = 0.82 + (0.18 * (year - recentStart)) / 2;
  } else {
    const span = Math.max(recentStart - startYear, 1);
    t = 0.06 + 0.64 * ((year - startYear) / span);
  }

  t = Math.min(1, Math.max(0, t));
  const r = lerp(FILL_LIGHT.r, FILL_DARK.r, t);
  const g = lerp(FILL_LIGHT.g, FILL_DARK.g, t);
  const b = lerp(FILL_LIGHT.b, FILL_DARK.b, t);
  return `rgb(${r}, ${g}, ${b})`;
}

export function SourceRecencyCard({ stats }: SourceRecencyCardProps) {
  if (!stats || stats.total === 0) {
    return (
      <ProjectStatCard
        title="SOURCE RECENCY"
        subtitle="Save sources to see when they were published"
      >
        <p className="py-6 text-center text-sm text-gray-500">No saved sources yet.</p>
      </ProjectStatCard>
    );
  }

  const { bars, sinceYear, sinceCount, startYear, presentYear } = stats;
  const darkSample = recencyBarFill(presentYear, startYear, presentYear);
  const lightSample = recencyBarFill(startYear, startYear, presentYear);

  // Sparse year benchmarks (e.g. 2017, 2019, 2021, 2023) — not every bar
  const yearTicks = (() => {
    const years = bars.map((b) => Number(b.year));
    if (years.length === 0) return [] as string[];
    if (years.length <= 4) return bars.map((b) => b.year);
    const start = years[0]!;
    const end = years[years.length - 1]!;
    const first = start % 2 === 1 ? start : start + 1;
    const ticks: string[] = [];
    for (let y = first; y <= end; y += 2) {
      ticks.push(String(y));
    }
    return ticks;
  })();

  return (
    <ProjectStatCard
      title="SOURCE RECENCY"
      subtitle={`${sinceCount} source${sinceCount === 1 ? "" : "s"} from ${sinceYear} onwards`}
      badge={
        <span className="rounded-full bg-metrics-bg px-2 py-0.5 text-xs font-medium text-metrics">
          {sinceCount} since {sinceYear}
        </span>
      }
    >
      <ResponsiveContainer width="100%" height={112}>
        <BarChart data={bars} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
          <XAxis
            dataKey="year"
            ticks={yearTicks}
            tick={{ fontSize: 10, fill: "#6b7280" }}
            tickLine={false}
            axisLine={false}
            interval={0}
          />
          <YAxis hide />
          <Tooltip
            cursor={{ fill: "rgba(136, 45, 96, 0.06)" }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const year = String(payload[0]?.payload?.year ?? "");
              const count = Number(payload[0]?.value ?? 0);
              return (
                <div className="rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-xs shadow-md">
                  <p className="font-semibold text-gray-900">{year}</p>
                  <p className="text-gray-600">
                    {count} source{count === 1 ? "" : "s"}
                  </p>
                </div>
              );
            }}
          />
          <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={28}>
            {bars.map((entry) => (
              <Cell
                key={entry.year}
                fill={recencyBarFill(Number(entry.year), startYear, presentYear)}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <div className="mt-3 flex items-center gap-4 text-xs text-gray-600">
        <span className="flex items-center gap-1.5">
          <span
            className="inline-block h-2 w-2 rounded-full"
            style={{ background: darkSample }}
          />
          Last 3 years
        </span>
        <span className="flex items-center gap-1.5">
          <span
            className="inline-block h-2 w-2 rounded-full"
            style={{ background: lightSample }}
          />
          Earlier
        </span>
      </div>
    </ProjectStatCard>
  );
}
