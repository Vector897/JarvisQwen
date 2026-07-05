import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/** 魔法链接：访问 http://<host>/?k=<访问码> 时，把码写入 aaos_access cookie 并跳到干净 URL。
 *  之后所有 /api 请求（经 Next 反代）都带上该 cookie，后端 AccessGateMiddleware 校验。
 *  未设访问码时后端完全放行，此逻辑无副作用。 */
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

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.).*)"],
};
