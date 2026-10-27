// Keep the review page on formerly.uk, where Cloudflare Access guards it.
// (The admin API checks the Access signature itself, so it is safe on any hostname.)

export async function onRequest({ request, next }) {
  const url = new URL(request.url);
  if (url.hostname !== "formerly.uk" && url.hostname !== "localhost" && url.hostname !== "127.0.0.1" && url.pathname.startsWith("/review")) {
    return Response.redirect(`https://formerly.uk${url.pathname}${url.search}`, 302);
  }
  const res = await next();
  if (url.pathname.startsWith("/review")) {
    const h = new Headers(res.headers);
    h.set("X-Robots-Tag", "noindex");
    h.set("Cache-Control", "no-store, no-transform");
    return new Response(res.body, { status: res.status, headers: h });
  }
  return res;
}
