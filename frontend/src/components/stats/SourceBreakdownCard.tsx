import { Cell, Pie, PieChart, ResponsiveContainer } from "recharts";

import type { SourceBreakdownItem } from "@/api/stats";

interface SourceBreakdownCardProps {
  data: SourceBreakdownItem[];
}

export function SourceBreakdownCard({ data }: SourceBreakdownCardProps) {
  if (data.length === 0) {
    return (
      <div className="rounded-xl bg-surface-card p-4">
        <p className="text-xs font-semibold tracking-wide text-gray-500">SOURCE BREAKDOWN</p>
        <p className="mt-4 py-6 text-center text-sm text-gray-500">No saved sources yet.</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl bg-surface-card p-4">
      <p className="text-xs font-semibold tracking-wide text-gray-500">SOURCE BREAKDOWN</p>
      <div className="mt-3 flex items-center gap-4">
        <div className="h-24 w-24 shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                dataKey="value"
                cx="50%"
                cy="50%"
                innerRadius={28}
                outerRadius={44}
                stroke="none"
              >
                {data.map((entry) => (
                  <Cell key={entry.name} fill={entry.color} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="min-w-0 flex-1 space-y-2">
          {data.map((item) => (
            <div key={item.name} className="flex items-center justify-between gap-2 text-xs">
              <span className="flex min-w-0 items-center gap-2 text-gray-700">
                <span
                  className="h-2.5 w-2.5 shrink-0 rounded-full"
                  style={{ backgroundColor: item.color }}
                />
                {item.name}
              </span>
              <span className="shrink-0 font-medium text-gray-600">{item.value}%</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

