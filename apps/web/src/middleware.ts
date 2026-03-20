import { NextRequest, NextResponse } from "next/server";

/**
 * Middleware — lightweight auth gate.
 *
 * Protected routes: /org/*
 * Public routes: /auth/*, /
 *
 * We check for the access token in cookies (set by the auth store on login).
 * If absent, redirect to /auth/login.
 *
 * Note: this is a presence check only — expiry is validated server-side
 * by the API. The auth store handles the 401 → clearAuth → redirect flow.
 */

const PUBLIC_PREFIXES = ["/auth", "/_next", "/favicon"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Always allow public routes
  if (PUBLIC_PREFIXES.some((p) => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  // Root → redirect to login (handled by page.tsx, but belt-and-suspenders)
  if (pathname === "/") {
    return NextResponse.redirect(new URL("/auth/login", request.url));
  }

  // Protected: /org/*
  if (pathname.startsWith("/org")) {
    // Check for token cookie — set by auth store
    // In this architecture, auth state lives in localStorage (client-side).
    // The org layout itself enforces the guard via useAuthStore.hydrate().
    // Middleware handles server-side redirect only when a cookie is present.
    const token = request.cookies.get("orbsys_access_token")?.value;
    if (!token) {
      // No cookie: redirect to login. The org layout will also catch this
      // client-side — belt-and-suspenders.
      const loginUrl = new URL("/auth/login", request.url);
      loginUrl.searchParams.set("next", pathname);
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
