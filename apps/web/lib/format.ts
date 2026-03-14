const ROLE_LABELS: Record<string, string> = {
  USER_ROLE_FREELANCER: "Freelancer",
  USER_ROLE_CLIENT: "Client",
  USER_ROLE_ADMIN: "Admin",
  FREELANCER: "Freelancer",
  CLIENT: "Client",
};

export function formatRole(role: string): string {
  return ROLE_LABELS[role] ?? role;
}

export function isFreelancer(role: string): boolean {
  return role === "USER_ROLE_FREELANCER" || role === "FREELANCER";
}

export function isClient(role: string): boolean {
  return role === "USER_ROLE_CLIENT" || role === "CLIENT";
}

/**
 * Convert a raw on-chain amount string to human-readable format.
 * USDC: 6 decimals (1000000 → "1.00")
 * SOL/ETH: 9 decimals (1000000000 → "1.00")
 */
export function formatAmount(raw: string, currency?: string): string {
  const n = parseInt(raw, 10);
  if (isNaN(n)) return raw;
  const decimals = currency === "USDC" ? 6 : 9;
  const human = n / 10 ** decimals;
  // Show up to 2 decimal places, strip trailing zeros
  if (human >= 1)
    return human.toLocaleString("en-US", {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    });
  // For tiny amounts, show more precision
  return human.toLocaleString("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 6,
  });
}

/**
 * Format amount with currency label: "2,250 USDC" or "1.5 SOL"
 */
export function formatAmountWithCurrency(
  raw: string,
  currency: string,
): string {
  return `${formatAmount(raw, currency)} ${currency}`;
}
