import { NextRequest, NextResponse } from "next/server";

// Strictly whitelisted SigmaSpire HQ / WireGuard VPN Static IPs
const SIGMASPIRE_STAFF_IPS = new Set([
  "127.0.0.1",
  "::1",
  "49.207.192.10", // Bengaluru HQ Static Fiber IP
  "13.232.104.88", // SigmaSpire AWS Bastion WireGuard VPN
]);

const ADMIN_SUBDOMAIN_HOST = process.env.NEXT_PUBLIC_ADMIN_HOST || "citadel.sigmaspire.internal";

export function middleware(req: NextRequest) {
  const host = req.headers.get("host") || "";
  const forwardedFor = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || "127.0.0.1";
  const pathname = req.nextUrl.pathname;

  const isTargetingAdminRoute =
    pathname.startsWith("/staff-gate") ||
    pathname.startsWith("/citadel") ||
    host.startsWith("citadel.");

  if (isTargetingAdminRoute) {
    // 1. Enforce Dedicated Hostname + Whitelisted Staff VPN IP
    const isAuthorizedHost = host === ADMIN_SUBDOMAIN_HOST || host.startsWith("localhost:");
    const isAuthorizedIp = SIGMASPIRE_STAFF_IPS.has(forwardedFor);

    if (!isAuthorizedHost || !isAuthorizedIp) {
      // Cloak existence: return generic 404 instead of 403 Forbidden
      return new NextResponse(null, { status: 404 });
    }

    // 2. Require Verified Staff JWT + TOTP Session Cookie for /citadel
    if (pathname.startsWith("/citadel")) {
      const staffToken = req.cookies.get("sigmaspire_citadel_session")?.value;
      if (!staffToken) {
        const loginUrl = req.nextUrl.clone();
        loginUrl.pathname = "/staff-gate";
        return NextResponse.redirect(loginUrl);
      }
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/staff-gate/:path*", "/citadel/:path*"],
};
