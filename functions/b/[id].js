// Short links used in social posts: formerly.uk/b/<listing id>
// Counts the arrival (daily tally per source, nothing about the visitor), then opens the
// site with that building shown first. Source: ?s=bluesky|newsletter|..., or Facebook's
// own fbclid parameter, which Facebook adds to every link people follow from it.
import { ensureSchema } from "../../lib/auth.js";

const SOURCES = new Set(["bluesky", "facebook", "instagram", "newsletter", "threads", "x", "linkedin"]);
let ready = false;
let known = null, knownAt = 0;

async function listings(env, request) {
  if (known && Date.now() - knownAt < 600_000) return known;
  const res = await env.ASSETS.fetch(new URL("/data/listings.json", request.url));
  known = new Map((await res.json()).listings.map((l) => [String(l.id), l]));
  knownAt = Date.now();
  return known;
}

export async function onRequestGet({ request, env, params }) {
  const url = new URL(request.url);
  const id = String(params.id || "").replace(/[^0-9]/g, "").slice(0, 10);
  const go = new URL(`/#b-${id}`, url.origin);
  try {
    let source = (url.searchParams.get("s") || "").toLowerCase();
    if (!SOURCES.has(source)) source = url.searchParams.has("fbclid") ? "facebook" : "";
    const l = id ? (await listings(env, request)).get(id) : null;
    if (source && l && env.DB) {
      if (!ready) { await ensureSchema(env.DB); ready = true; }
      const campaign = l.photo ? "listing-photo" : "listing-tile";
      await env.DB.prepare(`INSERT INTO visits (day, source, campaign, n) VALUES (date('now'), ?, ?, 1)
        ON CONFLICT(day, source, campaign) DO UPDATE SET n = n + 1`).bind(source, campaign).run();
    }
  } catch (e) { /* counting never blocks the visit */ }
  return Response.redirect(go.toString(), 302);
}
