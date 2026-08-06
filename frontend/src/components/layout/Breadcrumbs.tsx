import { Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";

interface BreadcrumbItem {
  label: string;
  to?: string;
}

interface BreadcrumbsProps {
  items: BreadcrumbItem[];
}

export function Breadcrumbs({ items }: BreadcrumbsProps) {
  return (
    <nav className="flex min-w-0 items-center gap-1 overflow-hidden whitespace-nowrap text-sm text-gray-500">
      {items.map((item, i) => {
        const isLast = i === items.length - 1;
        return (
          <span
            key={`${item.label}-${item.to ?? i}`}
            className={`flex min-w-0 items-center gap-1 ${
              isLast ? "flex-1" : "shrink-0 max-w-[10rem]"
            }`}
          >
            {i > 0 && <ChevronRight className="h-3 w-3 shrink-0" />}
            {item.to ? (
              <Link to={item.to} className="truncate hover:text-gray-700" title={item.label}>
                {item.label}
              </Link>
            ) : (
              <span className="truncate text-gray-700" title={item.label}>
                {item.label}
              </span>
            )}
          </span>
        );
      })}
    </nav>
  );
}
