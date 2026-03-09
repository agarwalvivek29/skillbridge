"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Briefcase,
  FolderOpen,
  Settings,
  Bell,
  User,
} from "lucide-react";
import { useAuthStore } from "@/lib/stores/auth";
import { cn } from "@/lib/utils";

const clientLinks = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/notifications", label: "Notifications", icon: Bell },
  { href: "/settings", label: "Settings", icon: Settings },
];

const freelancerLinks = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/dashboard/portfolio", label: "Portfolio", icon: FolderOpen },
  { href: "/notifications", label: "Notifications", icon: Bell },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const user = useAuthStore((s) => s.user);
  const links = user?.role === "FREELANCER" ? freelancerLinks : clientLinks;

  return (
    <div className="flex min-h-[calc(100vh-64px)]">
      {/* Desktop sidebar */}
      <aside className="hidden w-64 border-r border-neutral-200 bg-neutral-900 md:block">
        <nav className="flex flex-col gap-1 p-4">
          {links.map((link) => {
            const isActive = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2.5 text-sm transition-colors",
                  isActive
                    ? "border-l-[3px] border-primary-600 bg-neutral-800 text-white"
                    : "text-neutral-400 hover:text-neutral-100",
                )}
              >
                <link.icon className="h-5 w-5" />
                {link.label}
              </Link>
            );
          })}
          {user && (
            <Link
              href={`/profile/${user.wallet_address}`}
              className="mt-4 flex items-center gap-3 rounded-md px-3 py-2.5 text-sm text-neutral-400 transition-colors hover:text-neutral-100"
            >
              <User className="h-5 w-5" />
              My Profile
            </Link>
          )}
        </nav>
      </aside>

      {/* Main content */}
      <main className="flex-1 p-4 md:p-6">{children}</main>

      {/* Mobile bottom nav */}
      <nav className="fixed bottom-0 left-0 right-0 z-50 flex h-16 items-center justify-around border-t border-neutral-200 bg-white pb-[env(safe-area-inset-bottom)] md:hidden">
        {links.slice(0, 5).map((link) => {
          const isActive = pathname === link.href;
          return (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "flex flex-col items-center gap-0.5 text-xs",
                isActive ? "text-primary-600" : "text-neutral-400",
              )}
            >
              <link.icon className="h-5 w-5" />
              {link.label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
