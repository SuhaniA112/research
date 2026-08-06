import { Check, ChevronDown, Filter } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";

interface FilterMenuProps {
  label?: string;
  activeCount?: number;
  children: ReactNode;
  /** Wider panel for range controls / sort options */
  wide?: boolean;
}

/** Dropdown panel triggered by the shared Filter control. */
export function FilterMenu({
  label = "Filter",
  activeCount = 0,
  children,
  wide = false,
}: FilterMenuProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    if (open) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  return (
    <div ref={ref} className="relative shrink-0">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium ${
          activeCount > 0 || open
            ? "bg-brand-700 text-white"
            : "bg-brand-100 text-brand-700"
        }`}
        aria-expanded={open}
        aria-haspopup="dialog"
      >
        <Filter className="h-4 w-4" />
        {label}
        {activeCount > 0 && (
          <span className="rounded-full bg-white/20 px-1.5 text-xs text-white">
            {activeCount}
          </span>
        )}
      </button>
      {open && (
        <div
          className={`absolute right-0 z-20 mt-2 overflow-visible rounded-lg border border-gray-200 bg-white p-3 shadow-lg ${
            wide ? "w-80" : "w-64"
          }`}
        >
          {children}
        </div>
      )}
    </div>
  );
}

interface FilterOptionListProps {
  title: string;
  options: string[];
  selected: Set<string>;
  onToggle: (value: string) => void;
  onClear: () => void;
  emptyText?: string;
  /** Optional display labels keyed by option value */
  labels?: Record<string, string>;
}

export function FilterOptionList({
  title,
  options,
  selected,
  onToggle,
  onClear,
  emptyText = "No options yet.",
  labels,
}: FilterOptionListProps) {
  return (
    <div>
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="text-xs font-semibold tracking-wide text-gray-500">{title}</p>
        {selected.size > 0 && (
          <button
            type="button"
            onClick={onClear}
            className="text-xs text-brand-700 hover:underline"
          >
            Clear
          </button>
        )}
      </div>
      {options.length === 0 ? (
        <p className="text-sm text-gray-500">{emptyText}</p>
      ) : (
        <div className="max-h-48 space-y-1 overflow-y-auto">
          {options.map((option) => {
            const checked = selected.has(option);
            return (
              <label
                key={option}
                className="flex cursor-pointer items-center gap-2 rounded px-1 py-1 text-sm text-gray-700 hover:bg-gray-50"
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => onToggle(option)}
                  className="rounded border-gray-300 text-brand-700 focus:ring-brand-700"
                />
                <span className="truncate">{labels?.[option] ?? option}</span>
              </label>
            );
          })}
        </div>
      )}
    </div>
  );
}

interface YearRangeSliderProps {
  min: number;
  max: number;
  from: number;
  to: number;
  onChange: (from: number, to: number) => void;
  onReset: () => void;
  /** Shown for the upper bound when `to === max` (e.g. "Present") */
  maxLabel?: string;
}

/** Dual-thumb year range slider. */
export function YearRangeSlider({
  min,
  max,
  from,
  to,
  onChange,
  onReset,
  maxLabel,
}: YearRangeSliderProps) {
  const span = Math.max(max - min, 1);
  const leftPct = ((from - min) / span) * 100;
  const rightPct = ((to - min) / span) * 100;
  const isFiltered = from > min || to < max;
  const toDisplay = to === max && maxLabel ? maxLabel : String(to);

  return (
    <div>
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="text-xs font-semibold tracking-wide text-gray-500">YEAR RANGE</p>
        {isFiltered && (
          <button
            type="button"
            onClick={onReset}
            className="text-xs text-brand-700 hover:underline"
          >
            Reset
          </button>
        )}
      </div>
      <div className="relative h-6">
        <div className="absolute left-0 right-0 top-1/2 h-1.5 -translate-y-1/2 rounded-full bg-gray-200" />
        <div
          className="absolute top-1/2 h-1.5 -translate-y-1/2 rounded-full bg-brand-700"
          style={{ left: `${leftPct}%`, right: `${100 - rightPct}%` }}
        />
        <input
          type="range"
          min={min}
          max={max}
          value={from}
          aria-label="From year"
          onChange={(e) => {
            const next = Number(e.target.value);
            onChange(Math.min(next, to), to);
          }}
          className="year-range-thumb absolute inset-0 z-[2] w-full appearance-none bg-transparent"
        />
        <input
          type="range"
          min={min}
          max={max}
          value={to}
          aria-label="To year"
          onChange={(e) => {
            const next = Number(e.target.value);
            onChange(from, Math.max(next, from));
          }}
          className="year-range-thumb absolute inset-0 z-[3] w-full appearance-none bg-transparent"
        />
      </div>
      <div className="mt-2 flex items-center justify-between text-sm font-medium text-gray-800">
        <span>{from}</span>
        <span className="text-xs font-normal text-gray-400">to</span>
        <span>{toDisplay}</span>
      </div>
      <style>{`
        .year-range-thumb {
          pointer-events: none;
        }
        .year-range-thumb::-webkit-slider-thumb {
          pointer-events: auto;
          -webkit-appearance: none;
          appearance: none;
          width: 16px;
          height: 16px;
          border-radius: 9999px;
          background: #1d4ed8;
          border: 2px solid white;
          box-shadow: 0 0 0 1px #93c5fd;
          cursor: pointer;
        }
        .year-range-thumb::-moz-range-thumb {
          pointer-events: auto;
          width: 16px;
          height: 16px;
          border-radius: 9999px;
          background: #1d4ed8;
          border: 2px solid white;
          box-shadow: 0 0 0 1px #93c5fd;
          cursor: pointer;
        }
        .year-range-thumb::-webkit-slider-runnable-track {
          background: transparent;
        }
        .year-range-thumb::-moz-range-track {
          background: transparent;
        }
      `}</style>
    </div>
  );
}

export type SourceSortOption =
  | "relevance"
  | "recent"
  | "oldest"
  | "citations"
  | "similarity";

export const SOURCE_SORT_LABELS: Record<SourceSortOption, string> = {
  relevance: "Most relevant",
  recent: "Most recent",
  oldest: "Oldest first",
  citations: "Most cited",
  similarity: "Most similar",
};

interface SortBySelectProps {
  value: SourceSortOption;
  onChange: (value: SourceSortOption) => void;
}

/** Shows the current sort; options open in a menu directly below. */
export function SortBySelect({ value, onChange }: SortBySelectProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const options = Object.keys(SOURCE_SORT_LABELS) as SourceSortOption[];

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    function handleKey(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    if (open) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("keydown", handleKey);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKey);
    };
  }, [open]);

  return (
    <div ref={ref} className="relative">
      <p className="mb-2 text-xs font-semibold tracking-wide text-gray-500">SORT BY</p>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
        className="flex w-full items-center justify-between rounded-lg border border-gray-300 bg-white px-3 py-2 text-left text-sm text-gray-800 hover:bg-gray-50 focus:border-brand-700 focus:outline-none focus:ring-1 focus:ring-brand-700"
      >
        <span>{SOURCE_SORT_LABELS[value]}</span>
        <ChevronDown
          className={`h-4 w-4 shrink-0 text-gray-400 transition-transform ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>
      {open && (
        <ul
          role="listbox"
          aria-label="Sort sources by"
          className="absolute left-0 right-0 top-full z-30 mt-1.5 overflow-hidden rounded-xl border border-white/10 bg-[#3a3a3c]/95 py-1.5 shadow-xl backdrop-blur-md"
        >
          {options.map((option) => {
            const selected = option === value;
            return (
              <li key={option} role="option" aria-selected={selected}>
                <button
                  type="button"
                  onClick={() => {
                    onChange(option);
                    setOpen(false);
                  }}
                  className={`flex w-full items-center gap-2.5 px-3 py-2 text-left text-sm text-white hover:bg-white/10 ${
                    selected ? "bg-white/5" : ""
                  }`}
                >
                  <span className="flex w-4 shrink-0 justify-center">
                    {selected && <Check className="h-3.5 w-3.5" strokeWidth={2.5} />}
                  </span>
                  <span>{SOURCE_SORT_LABELS[option]}</span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
