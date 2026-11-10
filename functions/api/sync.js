// Used only by the GitHub Actions sync job (verified by GitHub's OIDC signature).
//  GET            -> decisions not yet applied to the site
//  POST {pending} -> add new candidate listings to the review queue
//  POST {applied} -> mark decisions as now live
import { isSyncJob, json, ensureSchema } from "../../lib/auth.js";

let ready = false;

export async function onRequest({ request, env }) {
  if (!(await isSyncJob(request, env))) return json({ ok: false, error: "Forbidden" }, 403);
  const db = env.DB;
  if (!ready) { await ensureSchema(db); ready = true; }

  if (request.method === "GET") {
    const approved = await db.prepare("SELECT id, data FROM pending WHERE status='approved' AND applied=0").all();
    const rejected = await db.prepare("SELECT id FROM pending WHERE status='rejected' AND applied=0").all();
    const removals = await db.prepare("SELECT id, reason FROM removals WHERE applied=0").all();
    const queued = await db.prepare("SELECT id FROM pending").all();
    const social = await db.prepare("SELECT id, pref, set_at FROM social").all();
    const closer = await db.prepare("SELECT id, data, decided FROM pending WHERE status='closer' ORDER BY decided").all();
    return json({
      ok: true,
      approved: approved.results.map((r) => ({ id: r.id, data: JSON.parse(r.data) })),
      rejected: rejected.results.map((r) => r.id),
      removals: removals.results,
      known: queued.results.map((r) => r.id),
      social: social.results,
      closer: closer.results.map((r) => ({ id: r.id, data: JSON.parse(r.data), decided: r.decided })),
    });
  }

  if (request.method === "POST") {
    const b = await request.json();
    const stmts = [];
    for (const item of b.pending || []) {
      const id = String(item.id || "");
      if (!/^\d{5,10}$/.test(id)) continue;
      // New candidates are added; ones still waiting pick up a photo suggestion added since
      stmts.push(db.prepare(`INSERT INTO pending (id, data, created) VALUES (?, ?, datetime('now'))
        ON CONFLICT(id) DO UPDATE SET data = excluded.data
        WHERE pending.status = 'pending' AND ((json_type(excluded.data, '$.ph') IS NOT NULL
          AND json_extract(pending.data, '$.ph[0]') IS NOT json_extract(excluded.data, '$.ph[0]'))
          -- or the card was moved between formerly. and grandly.
          OR IFNULL(json_extract(pending.data, '$.s'), 'formerly') IS NOT IFNULL(json_extract(excluded.data, '$.s'), 'formerly'))`).bind(id, JSON.stringify(item)));
      // A "Look closer" card comes back as a full card (page read, no "card" flag): it returns to the queue
      const isCard = item.card || /^EMAIL ONLY/i.test(String(item.why || ""));
      if (!isCard) stmts.push(db.prepare(`UPDATE pending SET data=?, status='pending', reason=NULL, decided=NULL
        WHERE id=? AND status='closer' AND applied=0`).bind(JSON.stringify(item), id));
    }
    const a = b.applied || {};
    for (const id of a.approved || []) stmts.push(db.prepare("UPDATE pending SET applied=1 WHERE id=? AND status='approved'").bind(String(id)));
    for (const id of a.rejected || []) stmts.push(db.prepare("UPDATE pending SET applied=1 WHERE id=? AND status='rejected'").bind(String(id)));
    for (const id of a.removals || []) stmts.push(db.prepare("UPDATE removals SET applied=1 WHERE id=?").bind(String(id)));
    if (stmts.length) await db.batch(stmts);
    return json({ ok: true, changed: stmts.length });
  }

  return json({ ok: false, error: "Method not allowed" }, 405);
}
