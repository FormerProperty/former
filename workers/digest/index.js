// formerly. weekly review summary.
// A Cloudflare Worker (name: formerly-digest) run by a cron trigger each Monday morning.
// Bindings: DB (D1 "formerly"), MAIL (send_email, restricted to the verified address below).
// Deployed by Cloudflare Workers Builds from this folder (see wrangler.toml).
import { EmailMessage } from "cloudflare:email";

const TO = "tanya@tanyapark.com";
const FROM = "digest@formerly.uk";
const SITE = "https://formerly.uk";

const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

async function gather(env) {
  const q = (sql, ...a) => env.DB.prepare(sql).bind(...a).all().then((r) => r.results).catch(() => []);
  const one = (sql) => env.DB.prepare(sql).first("n").catch(() => 0);
  const [newReports, openReports, pending, approved, rejected, removed] = await Promise.all([
    q("SELECT listing_id, reason, note, created FROM reports WHERE created >= datetime('now','-7 days') ORDER BY created"),
    one("SELECT COUNT(DISTINCT listing_id) n FROM reports WHERE status='open'"),
    one("SELECT COUNT(*) n FROM pending WHERE status='pending'"),
    one("SELECT COUNT(*) n FROM pending WHERE status='approved' AND decided >= datetime('now','-7 days')"),
    one("SELECT COUNT(*) n FROM pending WHERE status='rejected' AND decided >= datetime('now','-7 days')"),
    one("SELECT COUNT(*) n FROM removals WHERE decided >= datetime('now','-7 days')"),
  ]);
  let names = new Map();
  try {
    const d = await (await fetch(`${SITE}/data/listings.json`)).json();
    names = new Map(d.listings.map((l) => [String(l.id), `${l.label || "Former " + l.was}, ${l.place}`]));
  } catch {}
  return { newReports, openReports, pending, approved, rejected, removed, names };
}

function compose(g) {
  const lines = [];
  const html = [];
  const headline = [
    g.pending ? `${g.pending} waiting for approval` : "Nothing waiting for approval",
    g.openReports ? `${g.openReports} reported listing${g.openReports > 1 ? "s" : ""} open` : "no open reports",
  ].join(", ");
  lines.push(`formerly. this week: ${headline}.`, "");
  html.push(`<p style="font:16px/1.5 Georgia,serif;margin:0 0 16px">${esc(headline)}.</p>`);

  if (g.newReports.length) {
    lines.push(`New reports (${g.newReports.length}):`);
    html.push(`<p style="font:600 13px Arial,sans-serif;letter-spacing:.08em;text-transform:uppercase;color:#7B2D26;margin:20px 0 6px">New reports (${g.newReports.length})</p><ul style="padding-left:18px;margin:0;font:15px/1.5 Arial,sans-serif">`);
    for (const r of g.newReports) {
      const name = g.names.get(String(r.listing_id)) || `Listing ${r.listing_id}`;
      lines.push(`- ${name}: ${r.reason}${r.note ? ` ("${r.note}")` : ""}`);
      html.push(`<li><b>${esc(name)}</b>: ${esc(r.reason)}${r.note ? ` <i>"${esc(r.note)}"</i>` : ""}</li>`);
    }
    lines.push("");
    html.push("</ul>");
  } else {
    lines.push("No new reports this week.", "");
    html.push(`<p style="font:15px Arial,sans-serif;color:#5E625F">No new reports this week.</p>`);
  }

  const done = `Decided in the last 7 days: ${g.approved} approved, ${g.rejected} rejected, ${g.removed} taken down.`;
  lines.push(done, "", `Review: ${SITE}/review`);
  html.push(`<p style="font:15px Arial,sans-serif;color:#5E625F;margin-top:20px">${esc(done)}</p>`,
    `<p style="margin-top:20px"><a href="${SITE}/review" style="background:#1E4D3B;color:#fff;padding:10px 16px;text-decoration:none;font:600 15px Arial,sans-serif">Open the review page</a></p>`);
  return { subject: `formerly. weekly: ${headline}`, text: lines.join("\n"), html: html.join("\n") };
}

function mime({ subject, text, html }) {
  const b = "formerly-" + crypto.randomUUID();
  const enc = (s) => btoa(unescape(encodeURIComponent(s))).replace(/.{76}/g, "$&\r\n");
  return [
    `From: formerly. <${FROM}>`,
    `To: ${TO}`,
    `Subject: =?UTF-8?B?${btoa(unescape(encodeURIComponent(subject)))}?=`,
    `Date: ${new Date().toUTCString()}`,
    `Message-ID: <${crypto.randomUUID()}@formerly.uk>`,
    "MIME-Version: 1.0",
    `Content-Type: multipart/alternative; boundary="${b}"`,
    "",
    `--${b}`, "Content-Type: text/plain; charset=utf-8", "Content-Transfer-Encoding: base64", "", enc(text),
    `--${b}`, "Content-Type: text/html; charset=utf-8", "Content-Transfer-Encoding: base64", "", enc(html),
    `--${b}--`, "",
  ].join("\r\n");
}

async function send(env) {
  const g = await gather(env);
  const msg = compose(g);
  await env.MAIL.send(new EmailMessage(FROM, TO, mime(msg)));
  return msg.subject;
}

export default {
  async scheduled(event, env, ctx) {
    ctx.waitUntil(send(env));
  },
  // No public preview: the summary is admin data
  async fetch() {
    return new Response("Not found", { status: 404 });
  },
};
