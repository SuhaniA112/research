import { type ReactNode } from "react";

interface PillButtonProps {
  children: ReactNode;
  active?: boolean;
  onClick?: () => void;
}

export function PillButton({ children, active = false, onClick }: PillButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
        active
          ? "bg-brand-700 text-white"
          : "border border-gray-300 bg-white text-gray-600 hover:border-gray-400"
      }`}
    >
      {children}
    </button>
  );
}
