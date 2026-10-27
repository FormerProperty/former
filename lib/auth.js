// Signature checks for the two kinds of signed-in caller:
//  - Tanya, through Cloudflare Access (review page and admin API)
//  - the GitHub Actions sync job, through GitHub's OIDC tokens
// Both are RS256 JSON Web Tokens checked against the issuer's published keys,
// so no shared secret has to be stored anywhere.

const keyCache = new Map();

function b64url(s) {
  s = s.replace(/-/g, "+").replace(/_/g, "/");
  while (s.length % 4) s += "=";
  return Uint8Array.from(atob(s), (c) => c.charCodeAt(0));
}

async function keysFor(url) {
  const hit = keyCache.get(url);
  if (hit && hit.at > Date.now() - 3600_000) return hit.keys;
  const res = await fetch(url, { cf: { cacheTtl: 3600 } });
  if (!res.ok) throw new Error("key fetch failed");
  const keys = (await res.json()).keys || [];
  keyCache.set(url, { at: Date.now(), keys });
  return keys;
}

export async function verifyJwt(token, { jwksUrl, issuer, audience }) {
  if (!token) throw new Error("no token");
  const [h, p, s] = token.split(".");
  if (!h || !p || !s) throw new Error("malformed token");
  const dec = new TextDecoder();
  const header = JSON.parse(dec.decode(b64url(h)));
  const claims = JSON.parse(dec.decode(b64url(p)));
  if (header.alg !== "RS256") throw new Error("bad alg");

  let keys = await keysFor(jwksUrl);
  let jwk = keys.find((k) => k.kid === header.kid);
  if (!jwk) { keyCache.delete(jwksUrl); keys = await keysFor(jwksUrl); jwk = keys.find((k) => k.kid === header.kid); }
  if (!jwk) throw new Error("unknown key");

  const key = await crypto.subtle.importKey(
    "jwk", { kty: jwk.kty, n: jwk.n, e: jwk.e, alg: "RS256", ext: true },
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["verify"]);
  const ok = await crypto.subtle.verify("RSASSA-PKCS1-v1_5", key, b64url(s), new TextEncoder().encode(`${h}.${p}`));
  if (!ok) throw new Error("bad signature");

  const now = Math.floor(Date.now() / 1000);
  if (claims.exp && claims.exp < now - 30) throw new Error("expired");
  if (claims.nbf && claims.nbf > now + 30) throw new Error("not yet valid");
  if (issuer && claims.iss !== issuer) throw new Error("bad issuer");
  const aud = Array.isArray(claims.aud) ? claims.aud : [claims.aud];
  if (audience && !aud.includes(audience)) throw new Error("bad audience");
  return claims;
}

function cookie(request, name) {
  const m = (request.headers.get("Cookie") || "").match(new RegExp(`(?:^|;\\s*)${name}=([^;]+)`));
  return m ? m[1] : null;
}

// Returns the signed-in admin's email, or null.
export async function adminEmail(request, env) {
  const url = new URL(request.url);
  if (env.DEV_AUTH_BYPASS === "yes" && (url.hostname === "localhost" || url.hostname === "127.0.0.1")) return "dev@localhost";
  if (!env.ACCESS_TEAM || !env.ACCESS_AUD) return null;
  const token = request.headers.get("Cf-Access-Jwt-Assertion") || cookie(request, "CF_Authorization");
  try {
    const team = `https://${env.ACCESS_TEAM}.cloudflareaccess.com`;
    const claims = await verifyJwt(token, { jwksUrl: `${team}/cdn-cgi/access/certs`, issuer: team, audience: env.ACCESS_AUD });
    const allowed = (env.ADMIN_EMAILS || "").toLowerCase().split(",").map((s) => s.trim()).filter(Boolean);
    const email = (claims.email || "").toLowerCase();
    return allowed.includes(email) ? email : null;
  } catch {
    return null;
  }
}

// True when the caller is the sync workflow running on main in this repository.
export async function isSyncJob(request, env) {
  const auth = request.headers.get("Authorization") || "";
  const token = auth.startsWith("Bearer ") ? auth.slice(7) : null;
  try {
    const claims = await verifyJwt(token, {
      jwksUrl: "https://token.actions.githubusercontent.com/.well-known/jwks",
      issuer: "https://token.actions.githubusercontent.com",
      audience: env.SYNC_AUDIENCE,
    });
    return claims.repository === env.GH_REPO && claims.ref === "refs/heads/main";
  } catch {
    return false;
  }
}

export const json = (data, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" },
  });

export async function ensureSchema(db) {
  await db.batch([
    db.prepare(`CREATE TABLE IF NOT EXISTS reports (
      id INTEGER PRIMARY KEY AUTOINCREMENT, listing_id TEXT NOT NULL, reason TEXT NOT NULL, note TEXT,
      created TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'open', decided TEXT)`),
    db.prepare(`CREATE INDEX IF NOT EXISTS reports_listing ON reports(listing_id, status)`),
    db.prepare(`CREATE TABLE IF NOT EXISTS pending (
      id TEXT PRIMARY KEY, data TEXT NOT NULL, created TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
      reason TEXT, decided TEXT, applied INTEGER NOT NULL DEFAULT 0)`),
    db.prepare(`CREATE TABLE IF NOT EXISTS removals (
      id TEXT PRIMARY KEY, reason TEXT, decided TEXT NOT NULL, applied INTEGER NOT NULL DEFAULT 0)`),
    db.prepare(`CREATE TABLE IF NOT EXISTS visits (
      day TEXT NOT NULL, source TEXT NOT NULL, campaign TEXT NOT NULL DEFAULT '', n INTEGER NOT NULL DEFAULT 0,
      PRIMARY KEY (day, source, campaign))`),
  ]);
}
