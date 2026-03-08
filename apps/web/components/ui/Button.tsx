import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";
import { Spinner } from "./Spinner";

const variantStyles = {
  primary:
    "bg-primary-600 text-white hover:bg-primary-700 active:bg-primary-800 focus:ring-primary-400",
  secondary:
    "bg-secondary-500 text-white hover:bg-secondary-600 active:bg-secondary-700 focus:ring-secondary-400",
  outline:
    "border border-neutral-300 bg-transparent text-neutral-700 hover:bg-neutral-50 active:bg-neutral-100 focus:ring-primary-400",
  ghost:
    "bg-transparent text-neutral-700 hover:bg-neutral-100 active:bg-neutral-200 focus:ring-primary-400",
  destructive:
    "bg-error-600 text-white hover:bg-[#B91C1C] active:bg-[#991B1B] focus:ring-error-500",
  web3: "bg-web3-500 text-white hover:bg-web3-600 active:bg-web3-700 focus:ring-web3-400",
} as const;

const sizeStyles = {
  sm: "h-8 px-3 text-sm",
  md: "h-10 px-5 text-sm",
  lg: "h-12 px-6 text-base",
} as const;

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof variantStyles;
  size?: keyof typeof sizeStyles;
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = "primary",
      size = "md",
      loading = false,
      disabled,
      className,
      children,
      ...props
    },
    ref,
  ) => {
    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={cn(
          "inline-flex items-center justify-center gap-2 rounded-md font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2",
          variantStyles[variant],
          sizeStyles[size],
          (disabled || loading) && "pointer-events-none opacity-50",
          className,
        )}
        {...props}
      >
        {loading && (
          <Spinner size="sm" className="border-current border-t-transparent" />
        )}
        {children}
      </button>
    );
  },
);

Button.displayName = "Button";
