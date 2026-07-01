import { type ReactNode } from "react";

interface ProjectStatCardProps {
  title: string;
  subtitle?: string;
  badge?: ReactNode;
  children: ReactNode;
}

export function ProjectStatCard({ title, subtitle, badge, children }: ProjectStatCardProps) {
  return (
    <div className="rounded-xl bg-surface-card p-4">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xs font-semibold tracking-wide text-gray-500">{title}</p>
          {subtitle && <p className="mt-1 text-xs text-gray-500">{subtitle}</p>}
        </div>
        {badge}
      </div>
      <div className="mt-3">{children}</div>
    </div>
  );
}
