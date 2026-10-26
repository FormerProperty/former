// Public: a visitor reports a listing that does not fit. No personal data is stored.
import { json, ensureSchema } from "../../lib/auth.js";

const REASONS = new Set(["Always a house", "Flat in a larger building", "Barn conversion", "Sold or withdrawn", "Wrong details", "Other"]);
let ready = false;
let known = null, knownAt = 0;

async function listingIds(env, request) {
  if (known && Date.now() - knownAt < 600_000) return known;
  const res = await env.ASSETS.fetch(new URL("/data/listings.json", request.url));
  const data = await res.json();
  known = new Set(data.listings.map((l) => String(l.id)));
  knownAt = Date.now();
  return known;
}

export async function onRequestPost({ request, env }) {
  let body;
  try { body = await request.json(); } catch { return json({ ok: false, error: "Bad request" }, 400); }
  // Honeypot: real visitors never see or fill this field
  if (body.website) return json({ ok: true });
  const id = String(body.id || "");
  const reason = String(body.reason || "");
  const note = String(body.note || "").replace(/\s+/g, " ").trim().slice(0, 500);
  if (!/^\d{5,10}$/.test(id) || !REASONS.has(reason)) return json({ ok: false, error: "Bad request" }, 400);
  if (!(await listingIds(env, request)).has(id)) return json({ ok: false, error: "Unknown listing" }, 404);

  const db = env.DB;
  if (!ready) { await ensureSchema(db); ready = true; }
  // Simple flood limits: per listing, and per day overall
  const perListing = await db.prepare("SELECT COUNT(*) n FROM reports WHERE listing_id=? AND status='open'").bind(id).first("n");
  const today = await db.prepare("SELECT COUNT(*) n FROM reports WHERE created >= date('now')").first("n");
  if (perListing >= 20 || today >= 300) return json({ ok: true });

  await db.prepare("INSERT INTO reports (listing_id, reason, note, created) VALUES (?, ?, ?, datetime('now'))")
    .bind(id, reason, note || null).run();
  return json({ ok: true });
}
