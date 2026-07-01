import { type ReactNode } from "react";

interface StatCardProps {
  label: string;
  value: string;
  subtext?: string;
}

export function StatCard({ label, value, subtext }: StatCardProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5">
      <p className="text-xs font-semibold tracking-wide text-gray-500">{label}</p>
      <p className="mt-1 text-lg font-bold text-gray-900">{value}</p>
      {subtext && <p className="mt-0.5 text-xs text-gray-500">{subtext}</p>}
    </div>
  );
}

interface SelectionCardProps {
  icon: ReactNode;
  title: string;
  description: string;
  selected?: boolean;
  onClick?: () => void;
}

export function SelectionCard({
  icon,
  title,
  description,
  selected = false,
  onClick,
}: SelectionCardProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex flex-1 flex-col items-start rounded-xl border p-4 text-left transition-colors ${
        selected
          ? "border-brand-300 bg-brand-50"
          : "border-gray-200 bg-white hover:border-gray-300"
      }`}
    >
      <div className={`mb-2 ${selected ? "text-brand-700" : "text-gray-500"}`}>{icon}</div>
      <p className="font-semibold text-gray-900">{title}</p>
      <p className="mt-1 text-xs text-gray-500">{description}</p>
    </button>
  );
}
