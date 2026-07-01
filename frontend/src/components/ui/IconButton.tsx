import {
  type AnchorHTMLAttributes,
  type ButtonHTMLAttributes,
  type HTMLAttributes,
  type ReactNode,
} from "react";

export type IconControlSize = "sm" | "md" | "lg";

const sizeStyles: Record<IconControlSize, { control: string; icon: string }> = {
  sm: { control: "h-6 w-6", icon: "h-3.5 w-3.5" },
  md: { control: "h-7 w-7", icon: "h-4 w-4" },
  lg: { control: "h-8 w-8", icon: "h-5 w-5" },
};

export function getIconSizeClass(size: IconControlSize = "md"): string {
  return sizeStyles[size].icon;
}

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  size?: IconControlSize;
  children: ReactNode;
}

export function IconButton({
  size = "md",
  className = "",
  children,
  ...props
}: IconButtonProps) {
  return (
    <button
      type="button"
      className={`inline-flex shrink-0 items-center justify-center rounded-sm p-0 text-brand-700 transition-colors hover:bg-brand-50 ${sizeStyles[size].control} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

interface IconLinkProps extends AnchorHTMLAttributes<HTMLAnchorElement> {
  size?: IconControlSize;
  children: ReactNode;
}

export function IconLink({
  size = "md",
  className = "",
  children,
  ...props
}: IconLinkProps) {
  return (
    <a
      className={`inline-flex shrink-0 items-center justify-center rounded-sm p-0 text-brand-700 transition-colors hover:bg-brand-50 ${sizeStyles[size].control} ${className}`}
      {...props}
    >
      {children}
    </a>
  );
}

interface IconButtonGroupProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  direction?: "row" | "column";
}

export function IconButtonGroup({
  children,
  className = "",
  direction = "row",
  ...props
}: IconButtonGroupProps) {
  return (
    <div
      className={`flex shrink-0 items-center ${
        direction === "column" ? "flex-col" : "flex-row"
      } ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}
