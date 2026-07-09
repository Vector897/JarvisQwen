import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/** Magic link: when visiting http://<host>/?k=<access-code>, write the code into the
 *  aaos_access cookie and redirect to a clean URL.
 *  Afterwards every /api request (via the Next reverse proxy) carries this cookie, which
 *  the backend AccessGateMiddleware validates.
 *  When no access code is configured the backend lets everything through, so this logic
 *  has no side effects. */
export function middleware(req: NextRequest) {
  const k = req.nextUrl.searchParams.get("k");
  if (!k) return NextResponse.next();
  const url = req.nextUrl.clone();
  url.searchParams.delete("k");
  const res = NextResponse.redirect(url);
  res.cookies.set("aaos_access", k, {
    path: "/", sameSite: "lax", httpOnly: true, maxAge: 30 * 86400,
  });
  return res;
}

// Applies only to page navigation (excluding /api, _next, static files) — the magic link's ?k= only appears in page URLs.
export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|.*\\.).*)"],
};
