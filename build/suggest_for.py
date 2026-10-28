"""One-off helper: suggest Geograph photos for given listing ids (no changes made).
Usage: python build/suggest_for.py id1,id2,... > out.json"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import find_photos
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ids = sys.argv[1].split(",")
ls = {str(l["id"]): l for l in json.load(open(os.path.join(ROOT, "docs", "data", "listings.json")))["listings"]}
out = {}
for i in ids:
    l = ls.get(i)
    if l and l.get("lat"):
        try:
            out[i] = find_photos.suggest(l["lat"], l["lng"], l.get("type"))
        except Exception as e:
            out[i] = str(e)
print(json.dumps(out, indent=1, ensure_ascii=False))
