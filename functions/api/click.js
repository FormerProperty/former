// Public: counts a click from formerly.uk through to a listing on Zoopla.
// Stores only a daily tally per listing: no IP address, no cookie, no visitor id.
import { json, ensureSchema } from "../../lib/auth.js";

let ready = false;
let known = null, knownAt = 0;

async function listingIds(env, request) {
  if (known && Date.now() - knownAt < 600_000) return known;
  const res = await env.ASSETS.fetch(new URL("/data/listings.json", request.url));
  const d = await res.json();
  known = new Set([...d.listings, ...(d.extras || [])].map((l) => String(l.id)));
  knownAt = Date.now();
  return known;
}

export async function onRequestPost({ request, env }) {
  let b;
  try { b = JSON.parse(await request.text()); } catch { return json({ ok: false }, 400); }
  const id = String(b.id || "");
  if (!/^\d{5,10}$/.test(id) || !(await listingIds(env, request)).has(id)) return json({ ok: false }, 400);
  const db = env.DB;
  if (!ready) { await ensureSchema(db); ready = true; }
  const today = await db.prepare("SELECT COALESCE(SUM(n),0) n FROM clicks WHERE day = date('now')").first("n");
  if (today >= 20000) return json({ ok: true });
  await db.prepare(`INSERT INTO clicks (day, id, n) VALUES (date('now'), ?, 1)
    ON CONFLICT(day, id) DO UPDATE SET n = n + 1`).bind(id).run();
  return json({ ok: true });
}
