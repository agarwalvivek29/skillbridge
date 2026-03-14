import Link from "next/link";

const footerLinks = {
  Platform: [
    { label: "Browse Gigs", href: "/gigs" },
    { label: "How It Works", href: "/about" },
    { label: "Post a Gig", href: "/gigs/new" },
  ],
  Resources: [
    { label: "About", href: "/about" },
    { label: "FAQ", href: "/about#faq" },
    { label: "Fee Structure", href: "/about#fees" },
  ],
  Legal: [
    { label: "Terms of Service", href: "/terms" },
    { label: "Privacy Policy", href: "/privacy" },
  ],
};

export function Footer() {
  return (
    <footer className="border-t border-neutral-200 bg-white">
      <div className="mx-auto max-w-[1280px] px-4 py-12 md:px-6">
        <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
          <div className="col-span-2 md:col-span-1">
            <Link href="/" className="flex items-center gap-1 text-xl">
              <span className="font-semibold text-primary-600">Skill</span>
              <span className="font-bold text-primary-600">Bridge</span>
            </Link>
            <p className="mt-3 text-sm text-neutral-500">
              AI-powered freelance platform with smart contract escrow on
              Solana.
            </p>
          </div>

          {Object.entries(footerLinks).map(([section, links]) => (
            <div key={section}>
              <h4 className="text-sm font-semibold text-neutral-800">
                {section}
              </h4>
              <ul className="mt-3 space-y-2">
                {links.map((link) => (
                  <li key={link.href}>
                    <Link
                      href={link.href}
                      className="text-sm text-neutral-500 transition-colors hover:text-neutral-900"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-10 flex flex-col items-center justify-between gap-4 border-t border-neutral-200 pt-6 md:flex-row">
          <p className="text-sm text-neutral-400">
            &copy; {new Date().getFullYear()} SkillBridge. All rights reserved.
          </p>
          <div className="flex items-center gap-4">
            <a
              href="https://github.com/agarwalvivek29/skillbridge"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-neutral-400 transition-colors hover:text-neutral-600"
            >
              GitHub
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
