import { Star } from "lucide-react";

import { getIconSizeClass, IconButton, type IconControlSize } from "@/components/ui/IconButton";

interface StarButtonProps {
  starred: boolean;
  onToggle: () => void;
  size?: IconControlSize;
  className?: string;
}

export function StarButton({
  starred,
  onToggle,
  size = "md",
  className = "",
}: StarButtonProps) {
  return (
    <IconButton
      size={size}
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        onToggle();
      }}
      className={`text-gray-300 hover:bg-transparent hover:text-yellow-400 ${className}`}
      aria-label={starred ? "Unstar" : "Star"}
      aria-pressed={starred}
      title={starred ? "Unstar" : "Star"}
    >
      <Star
        className={`${getIconSizeClass(size)} ${
          starred ? "fill-yellow-400 text-yellow-400" : ""
        }`}
      />
    </IconButton>
  );
}
