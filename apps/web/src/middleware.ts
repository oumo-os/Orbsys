import { NextRequest, NextResponse } from "next/server";

/**
 * Middleware — lightweight auth gate.
 *
 * Protected routes: /org/*
 * Public routes: /auth/*, /join, /setup, /me
 *
 * We check for the orbsys_session cookie (set by the auth store on login).
 * If absent on protected routes, redirect to /auth/login.
 *
 * Note: this is a presence check only — expiry is validated server-side
 * by the API. The auth store handles the 401 → clearAuth → redirect flow.
 */

const PUBLIC_PREFIXES = ["/auth", "/join", "/setup", "/me", "/_next", "/favicon"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Always allow public routes
  if (PUBLIC_PREFIXES.some((p) => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  // Root is handled by page.tsx (first-run detection) — allow through
  if (pathname === "/") {
    return NextResponse.next();
  }

  // Protected: /org/* — check for session cookie
  if (pathname.startsWith("/org")) {
    const sessionCookie = request.cookies.get("orbsys_session");
    if (!sessionCookie?.value) {
      const loginUrl = new URL("/auth/login", request.url);
      loginUrl.searchParams.set("redirect", pathname);
      return NextResponse.redirect(loginUrl);
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all routes except static files and Next.js internals.
     */
    "/((?!_next/static|_next/image|favicon.ico).*)",
  ],
};
