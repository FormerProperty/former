"""Copy the shared Cloudflare functions into grandly/, so the grandly Pages project (root
directory grandly/) has real files to deploy. Pages does not bundle imports from outside its
root directory, so re-exports did not work. Never edit the copies: edit functions/ or lib/
and run this (the hourly sync runs it too)."""
import os, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = ["functions/api/click.js", "functions/api/hit.js", "functions/api/report.js",
         "functions/b/[id].js", "lib/auth.js"]
NOTE = "// COPY of {0} for grandly.uk, made by build/copy_grandly_functions.py. Edit the original.\n"

for f in FILES:
    src, dst = os.path.join(ROOT, f), os.path.join(ROOT, "grandly", f)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    text = NOTE.format(f) + open(src).read()
    if not os.path.exists(dst) or open(dst).read() != text:
        open(dst, "w").write(text)
        print("copied", f)
