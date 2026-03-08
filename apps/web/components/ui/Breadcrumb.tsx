import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface BreadcrumbProps {
  items: BreadcrumbItem[];
  className?: string;
}

export function Breadcrumb({ items, className }: BreadcrumbProps) {
  return (
    <nav
      aria-label="Breadcrumb"
      className={cn("flex items-center gap-1.5 text-sm", className)}
    >
      {items.map((item, i) => {
        const isLast = i === items.length - 1;
        return (
          <span key={i} className="flex items-center gap-1.5">
            {i > 0 && <ChevronRight className="h-3.5 w-3.5 text-neutral-400" />}
            {item.href && !isLast ? (
              <Link
                href={item.href}
                className="text-neutral-500 transition-colors hover:text-neutral-700"
              >
                {item.label}
              </Link>
            ) : (
              <span className="font-medium text-neutral-800">{item.label}</span>
            )}
          </span>
        );
      })}
    </nav>
  );
}
