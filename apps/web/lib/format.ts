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
