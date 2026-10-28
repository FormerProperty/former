// Admin API for the review page. Every request must carry a valid Cloudflare Access login.
import { adminEmail, json, ensureSchema } from "../../../lib/auth.js";

let ready = false;

export async function onRequest(ctx) {
  const { request, env, params } = ctx;
  const who = await adminEmail(request, env);
  if (!who) return json({ ok: false, error: "Not signed in" }, 401);
  const db = env.DB;
  if (!ready) { await ensureSchema(db); ready = true; }
  const route = (params.path || []).join("/");

  if (request.method === "GET" && route === "queue") {
    const pending = await db.prepare("SELECT id, data, created FROM pending WHERE status='pending' ORDER BY created").all();
    const reports = await db.prepare("SELECT id, listing_id, reason, note, created FROM reports WHERE status='open' ORDER BY created").all();
    const recentPending = await db.prepare("SELECT id, data, status, reason, decided, applied FROM pending WHERE status!='pending' ORDER BY decided DESC LIMIT 15").all();
    const recentRemovals = await db.prepare("SELECT id, reason, decided, applied FROM removals ORDER BY decided DESC LIMIT 15").all();
    const visits = await db.prepare(`SELECT source,
        SUM(CASE WHEN day >= date('now','-6 days') THEN n ELSE 0 END) week,
        SUM(CASE WHEN day <  date('now','-6 days') AND day >= date('now','-13 days') THEN n ELSE 0 END) prev,
        SUM(n) month
      FROM visits WHERE day >= date('now','-29 days') GROUP BY source ORDER BY month DESC`).all();
    const clickTotals = await db.prepare(`SELECT
        COALESCE(SUM(CASE WHEN day >= date('now','-6 days') THEN n END),0) week,
        COALESCE(SUM(CASE WHEN day < date('now','-6 days') AND day >= date('now','-13 days') THEN n END),0) prev,
        COALESCE(SUM(n),0) month
      FROM clicks WHERE day >= date('now','-29 days')`).first();
    const clickTop = await db.prepare(`SELECT id, SUM(n) n FROM clicks WHERE day >= date('now','-29 days')
      GROUP BY id ORDER BY n DESC LIMIT 5`).all();
    const social = await db.prepare("SELECT id, pref, set_at FROM social ORDER BY set_at DESC").all();
    const dismissed = await db.prepare("SELECT listing_id, MAX(decided) decided, COUNT(*) n FROM reports WHERE status='dismissed' GROUP BY listing_id ORDER BY decided DESC LIMIT 10").all();
    return json({
      ok: true, who,
      pending: pending.results.map((r) => ({ ...r, data: JSON.parse(r.data) })),
      reports: reports.results,
      visits: visits.results,
      social: social.results,
      clicks: { ...clickTotals, top: clickTop.results },
      recent: {
        pending: recentPending.results.map((r) => ({ ...r, data: JSON.parse(r.data) })),
        removals: recentRemovals.results,
        dismissed: dismissed.results,
      },
    });
  }

  if (request.method === "POST" && route === "decide") {
    let b;
    try { b = await request.json(); } catch { return json({ ok: false, error: "Bad request" }, 400); }
    const id = String(b.id || "");
    const reason = String(b.reason || "").slice(0, 300) || null;
    if (!/^\d{5,10}$/.test(id)) return json({ ok: false, error: "Bad id" }, 400);

    if (b.type === "pending" && b.action === "approve" && b.edits) {
      const row = await db.prepare("SELECT data FROM pending WHERE id=? AND applied=0").bind(id).first();
      if (row) {
        const data = JSON.parse(row.data);
        if (typeof b.edits.h === "string") data.h = b.edits.h.replace(/\s+/g, " ").trim().slice(0, 90);
        if (typeof b.edits.photo === "boolean") data.phok = b.edits.photo;
        if (b.edits.social === "next")
          await db.prepare("INSERT INTO social (id, pref, set_at) VALUES (?, 'next', datetime('now')) ON CONFLICT(id) DO UPDATE SET pref='next', set_at=datetime('now')").bind(id).run();
        await db.prepare("UPDATE pending SET data=? WHERE id=?").bind(JSON.stringify(data), id).run();
      }
    }
    if (b.type === "pending" && (b.action === "approve" || b.action === "reject")) {
      const r = await db.prepare("UPDATE pending SET status=?, reason=?, decided=datetime('now') WHERE id=? AND applied=0")
        .bind(b.action === "approve" ? "approved" : "rejected", reason, id).run();
      return json({ ok: r.meta.changes > 0 });
    }
    if (b.type === "pending" && b.action === "undo") {
      const r = await db.prepare("UPDATE pending SET status='pending', reason=NULL, decided=NULL WHERE id=? AND applied=0").bind(id).run();
      return json({ ok: r.meta.changes > 0, error: r.meta.changes ? undefined : "Already live, so it can no longer be undone here" });
    }
    if (b.type === "report" && b.action === "remove") {
      const why = reason || (await db.prepare("SELECT reason FROM reports WHERE listing_id=? AND status='open' ORDER BY id DESC").bind(id).first("reason")) || "Reported";
      await db.batch([
        db.prepare("INSERT INTO removals (id, reason, decided) VALUES (?, ?, datetime('now')) ON CONFLICT(id) DO UPDATE SET reason=excluded.reason, decided=excluded.decided, applied=0").bind(id, why),
        db.prepare("UPDATE reports SET status='removed', decided=datetime('now') WHERE listing_id=? AND status='open'").bind(id),
      ]);
      return json({ ok: true });
    }
    if (b.type === "report" && b.action === "dismiss") {
      await db.prepare("UPDATE reports SET status='dismissed', decided=datetime('now') WHERE listing_id=? AND status='open'").bind(id).run();
      return json({ ok: true });
    }
    if (b.type === "removal" && b.action === "undo") {
      const r = await db.prepare("DELETE FROM removals WHERE id=? AND applied=0").bind(id).run();
      if (r.meta.changes) await db.prepare("UPDATE reports SET status='open', decided=NULL WHERE listing_id=? AND status='removed'").bind(id).run();
      return json({ ok: r.meta.changes > 0, error: r.meta.changes ? undefined : "Already taken down, so it can no longer be undone here" });
    }
    if (b.type === "dismissal" && b.action === "undo") {
      await db.prepare("UPDATE reports SET status='open', decided=NULL WHERE listing_id=? AND status='dismissed'").bind(id).run();
      return json({ ok: true });
    }
    return json({ ok: false, error: "Unknown action" }, 400);
  }

  // Social posting: "next" puts a building at the front of the queue, "never" keeps it off; null clears
  if (request.method === "POST" && route === "social") {
    let b;
    try { b = await request.json(); } catch { return json({ ok: false, error: "Bad request" }, 400); }
    const id = String(b.id || "");
    if (!/^\d{5,10}$/.test(id)) return json({ ok: false, error: "Bad id" }, 400);
    if (b.pref === "next" || b.pref === "never") {
      await db.prepare("INSERT INTO social (id, pref, set_at) VALUES (?, ?, datetime('now')) ON CONFLICT(id) DO UPDATE SET pref=excluded.pref, set_at=excluded.set_at").bind(id, b.pref).run();
    } else {
      await db.prepare("DELETE FROM social WHERE id=?").bind(id).run();
    }
    return json({ ok: true });
  }

  return json({ ok: false, error: "Not found" }, 404);
}
