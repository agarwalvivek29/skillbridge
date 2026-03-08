"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ConnectButton } from "@/components/web3/ConnectButton";

const navLinks = [
  { href: "/", label: "Home" },
  { href: "/gigs", label: "Browse Gigs" },
  { href: "/about", label: "About" },
];

export function NavBar() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 h-16 border-b border-neutral-200 bg-white">
      <div className="mx-auto flex h-full max-w-[1280px] items-center justify-between px-4 md:px-6">
        <Link href="/" className="flex items-center gap-1 text-xl">
          <span className="font-semibold text-primary-600">Skill</span>
          <span className="font-bold text-primary-600">Bridge</span>
        </Link>

        <nav className="hidden items-center gap-6 md:flex">
          {navLinks.map((link) => {
            const isActive = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`text-sm font-medium transition-colors ${
                  isActive
                    ? "border-b-2 border-primary-600 text-primary-600"
                    : "text-neutral-600 hover:text-neutral-900"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-3">
          <ConnectButton />
        </div>
      </div>
    </header>
  );
}
