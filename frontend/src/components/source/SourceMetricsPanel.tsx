import { Check } from "lucide-react";

import { ProgressBar } from "@/components/ui/ProgressBar";
import type { Source } from "@/types";

interface SourceMetricsPanelProps {
  source: Source;
  className?: string;
}

export function SourceMetricsPanel({ source, className = "" }: SourceMetricsPanelProps) {
  return (
    <div
      className={`flex w-52 shrink-0 flex-col justify-between border-l border-gray-200 bg-surface-card p-5 ${className}`}
    >
      <div className="space-y-5">
        <div>
          <p className="text-xs font-semibold tracking-wide text-gray-500">RELEVANCE</p>
          <p className="mt-0.5 text-sm font-bold text-metric-green">{source.relevance}%</p>
          <ProgressBar value={source.relevance} className="mt-1.5" />
          <p className="mt-2 text-[10px] font-semibold tracking-wide text-gray-500">RELEVANT TO:</p>
          <ul className="mt-1 space-y-0.5">
            {source.relevantTo.map((kw) => (
              <li key={kw} className="flex items-center gap-1.5 text-xs text-gray-700">
                <Check className="h-3 w-3 shrink-0 text-metric-green" strokeWidth={3} />
                {kw}
              </li>
            ))}
          </ul>
        </div>

        <div>
          <p className="text-xs font-semibold tracking-wide text-gray-500">SIMILARITY</p>
          <p className="mt-0.5 text-sm font-bold text-metric-green">{source.similarity}%</p>
          <ProgressBar value={source.similarity} className="mt-1.5" />
          <p className="mt-2 text-[10px] font-semibold tracking-wide text-gray-500">SIMILAR TO:</p>
          <ul className="mt-1 space-y-0.5">
            {source.similarTo.map((name) => (
              <li key={name} className="text-xs text-gray-700">
                {name}
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="mt-5">
        <p className="text-xs font-semibold tracking-wide text-gray-500">IMPACT</p>
        <p className="mt-1 text-xs text-gray-600">{source.citations} Citations</p>
        <p className="text-xs text-gray-600">Cites {source.citesSaved} sources you have saved.</p>
        <p className="text-xs text-gray-600">
          Cited by {source.citedBySaved} sources you have saved.
        </p>
      </div>
    </div>
  );
}
