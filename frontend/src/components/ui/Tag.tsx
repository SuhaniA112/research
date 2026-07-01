import { type ReactNode } from "react";

interface TagProps {
  children: ReactNode;
  variant?: "brand" | "metrics" | "outline";
  onRemove?: () => void;
}

const variantClasses = {
  brand: "bg-brand-100 text-brand-700",
  metrics: "bg-metrics-bg text-metrics",
  outline: "border border-gray-300 bg-white text-gray-700",
};

export function Tag({ children, variant = "brand", onRemove }: TagProps) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${variantClasses[variant]}`}
    >
      {children}
      {onRemove && (
        <button type="button" onClick={onRemove} className="ml-0.5 hover:opacity-70">
          ×
        </button>
      )}
    </span>
  );
}
