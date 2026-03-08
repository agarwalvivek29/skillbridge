import Image from "next/image";
import { cn } from "@/lib/utils";

const sizeStyles = {
  xs: "h-6 w-6 text-[10px]",
  sm: "h-8 w-8 text-xs",
  md: "h-10 w-10 text-sm",
  lg: "h-14 w-14 text-xl",
  xl: "h-20 w-20 text-[28px]",
} as const;

const sizePx = { xs: 24, sm: 32, md: 40, lg: 56, xl: 80 } as const;

interface AvatarProps {
  src?: string | null;
  alt?: string;
  name?: string | null;
  walletAddress?: string | null;
  size?: keyof typeof sizeStyles;
  className?: string;
}

function getFallback(name?: string | null, walletAddress?: string | null) {
  if (name) return name.charAt(0).toUpperCase();
  if (walletAddress) return walletAddress.slice(2, 4).toUpperCase();
  return "?";
}

export function Avatar({
  src,
  alt,
  name,
  walletAddress,
  size = "md",
  className,
}: AvatarProps) {
  const fallback = getFallback(name, walletAddress);
  const px = sizePx[size];

  if (src) {
    return (
      <Image
        src={src}
        alt={alt ?? name ?? "Avatar"}
        width={px}
        height={px}
        className={cn(
          "rounded-full border-2 border-white object-cover",
          sizeStyles[size],
          className,
        )}
      />
    );
  }

  return (
    <div
      className={cn(
        "flex items-center justify-center rounded-full border-2 border-white bg-primary-100 font-semibold text-primary-700",
        sizeStyles[size],
        className,
      )}
      aria-label={alt ?? name ?? "Avatar"}
    >
      {fallback}
    </div>
  );
}
