"""Sync review decisions between formerly.uk's database and this repository.

Runs in GitHub Actions (see .github/workflows/sync.yml). It proves who it is to
formerly.uk with a GitHub OIDC token, so no shared secret is stored anywhere.

1. Sends new candidate listings from pending/*.json to the review queue.
2. Fetches decisions not yet applied:
     approved -> appended to export/90-approved.json (goes live)
     rejected -> dropped from pending/
     removals -> added to removed.json (taken off the site)
3. Rebuilds the site data (build.py) and tells formerly.uk what is now live.
"""
import glob
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = os.environ.get("FORMERLY_API", "https://formerly.uk/api/sync")
AUDIENCE = "https://formerly.uk"


def oidc_token():
    url = os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"] + "&audience=" + urllib.parse.quote(AUDIENCE)
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"]})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["value"]


def call(method, token, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API, data=data, method=method, headers={
        "Authorization": "Bearer " + token, "Content-Type": "application/json", "User-Agent": "formerly-sync"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def load(path, default):
    try:
        with open(path) as fh:
            return json.load(fh)
    except FileNotFoundError:
        return default


def save(path, data):
    with open(path, "w") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
        fh.write("\n")


def main():
    token = oidc_token()

    # Only the dated candidate files; judged-out.json is an {id: reason} record, not candidates
    pending_files = sorted(f for f in glob.glob(os.path.join(ROOT, "pending", "*.json"))
                           if os.path.basename(f) != "judged-out.json")
    pending = {}
    for f in pending_files:
        for row in load(f, []):
            pending[str(row["id"])] = row
    if pending:
        res = call("POST", token, {"pending": list(pending.values())})
        print(f"queued {len(pending)} candidates ({res.get('changed')} statements)")

    d = call("GET", token)
    approved = {str(x["id"]): x["data"] for x in d["approved"]}
    rejected = set(map(str, d["rejected"]))
    removals = {str(x["id"]): x["reason"] for x in d["removals"]}
    print(f"decisions: {len(approved)} approved, {len(rejected)} rejected, {len(removals)} removals")
    if not (approved or rejected or removals):
        return 0

    # Approved rows join the published export (later export files win)
    out_path = os.path.join(ROOT, "export", "90-approved.json")
    out = {str(r["id"]): r for r in load(out_path, [])}
    for pid, row in approved.items():
        row = {k: v for k, v in row.items() if k in ("id", "p", "b", "a", "l", "t", "w", "n", "g", "au", "h", "sq", "ac", "gr", "bt", "ag", "ll")}
        row["id"] = pid
        out[pid] = row
    save(out_path, list(out.values()))

    removed_path = os.path.join(ROOT, "removed.json")
    removed = load(removed_path, {})
    for rid, reason in removals.items():
        removed[rid] = f"Taken down after a report: {reason}"
    save(removed_path, removed)

    # Decided candidates leave the pending folder
    decided = set(approved) | rejected
    for f in pending_files:
        rows = [r for r in load(f, []) if str(r["id"]) not in decided]
        if rows:
            save(f, rows)
        else:
            os.remove(f)

    env = dict(os.environ, FORMER_SITE_URL="https://formerly.uk/")
    subprocess.run([sys.executable, os.path.join(ROOT, "build", "build.py")], check=True, env=env)
    subprocess.run([sys.executable, os.path.join(ROOT, "build", "fetch_photos.py")], check=False)

    # Record what will be live once this commit is pushed
    with open(os.path.join(ROOT, ".sync-applied.json"), "w") as fh:
        json.dump({"approved": list(approved), "rejected": list(rejected), "removals": list(removals)}, fh)
    return 0


def ack():
    token = oidc_token()
    path = os.path.join(ROOT, ".sync-applied.json")
    applied = load(path, None)
    if applied:
        print(call("POST", token, {"applied": applied}))
        os.remove(path)


if __name__ == "__main__":
    sys.exit(ack() if sys.argv[1:] == ["ack"] else main())
