"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X } from "lucide-react";
import { ConnectButton } from "@/components/web3/ConnectButton";
import { NotificationBell } from "@/components/layout/NotificationBell";
import { useAuthStore } from "@/lib/stores/auth";
import { cn } from "@/lib/utils";

const navLinks = [
  { href: "/", label: "Home" },
  { href: "/gigs", label: "Browse Gigs" },
  { href: "/about", label: "About" },
];

export function NavBar() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const token = useAuthStore((s) => s.token);

  return (
    <header className="sticky top-0 z-50 border-b border-neutral-200 bg-white">
      <div className="mx-auto flex h-16 max-w-[1280px] items-center justify-between px-4 md:px-6">
        <Link href="/" className="flex items-center gap-1 text-xl">
          <span className="font-semibold text-primary-600">Skill</span>
          <span className="font-bold text-primary-600">Bridge</span>
        </Link>

        {/* Desktop nav */}
        <nav className="hidden items-center gap-6 md:flex">
          {navLinks.map((link) => {
            const isActive = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "text-sm font-medium transition-colors",
                  isActive
                    ? "border-b-2 border-primary-600 text-primary-600"
                    : "text-neutral-600 hover:text-neutral-900",
                )}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-3">
          {token && (
            <>
              <NotificationBell />
              <Link
                href="/dashboard"
                className={cn(
                  "hidden text-sm font-medium transition-colors md:block",
                  pathname.startsWith("/dashboard")
                    ? "text-primary-600"
                    : "text-neutral-600 hover:text-neutral-900",
                )}
              >
                Dashboard
              </Link>
            </>
          )}
          <ConnectButton />
          {/* Hamburger */}
          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            className="inline-flex h-10 w-10 items-center justify-center rounded-md text-neutral-600 hover:bg-neutral-100 md:hidden"
            aria-label={mobileOpen ? "Close menu" : "Open menu"}
          >
            {mobileOpen ? (
              <X className="h-5 w-5" />
            ) : (
              <Menu className="h-5 w-5" />
            )}
          </button>
        </div>
      </div>

      {/* Mobile dropdown */}
      {mobileOpen && (
        <nav className="border-t border-neutral-200 bg-white px-4 pb-4 md:hidden">
          {navLinks.map((link) => {
            const isActive = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileOpen(false)}
                className={cn(
                  "block py-3 text-base font-medium transition-colors min-h-[44px] flex items-center",
                  isActive
                    ? "text-primary-600"
                    : "text-neutral-600 hover:text-neutral-900",
                )}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
      )}
    </header>
  );
}
