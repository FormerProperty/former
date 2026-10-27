// Public: counts a visit that arrived through a tagged link (utm_source).
// Stores only a daily tally per source and campaign: no IP address, no cookie, no visitor id.
import { json, ensureSchema } from "../../lib/auth.js";

const SOURCES = new Set(["bluesky", "facebook", "instagram", "newsletter", "threads", "x", "linkedin"]);
let ready = false;

export async function onRequestPost({ request, env }) {
  let b;
  try { b = await request.json(); } catch { return json({ ok: false }, 400); }
  let source = String(b.s || "").toLowerCase().trim().slice(0, 30);
  if (!source) return json({ ok: false }, 400);
  if (!SOURCES.has(source)) source = "other";
  const campaign = String(b.c || "").toLowerCase().replace(/[^a-z0-9-]/g, "").slice(0, 40);

  const db = env.DB;
  if (!ready) { await ensureSchema(db); ready = true; }
  // Flood limit: tagged arrivals beyond this in a day are not counted
  const today = await db.prepare("SELECT COALESCE(SUM(n),0) n FROM visits WHERE day = date('now')").first("n");
  if (today >= 5000) return json({ ok: true });
  await db.prepare(`INSERT INTO visits (day, source, campaign, n) VALUES (date('now'), ?, ?, 1)
    ON CONFLICT(day, source, campaign) DO UPDATE SET n = n + 1`).bind(source, campaign).run();
  return json({ ok: true });
}
