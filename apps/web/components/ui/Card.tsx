import { cn } from "@/lib/utils";
import { type HTMLAttributes } from "react";

const variantStyles = {
  flat: "border border-neutral-200 bg-white",
  elevated: "bg-white shadow-md",
  bordered: "border border-neutral-200 bg-white shadow-sm",
} as const;

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: keyof typeof variantStyles;
}

export function Card({
  variant = "bordered",
  className,
  children,
  ...props
}: CardProps) {
  return (
    <div
      className={cn("rounded-lg p-4 md:p-6", variantStyles[variant], className)}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({
  className,
  children,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("border-b border-neutral-200 pb-4", className)}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardFooter({
  className,
  children,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("border-t border-neutral-200 pt-4", className)}
      {...props}
    >
      {children}
    </div>
  );
}
