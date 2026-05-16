"""
Generic catalog audit for any data module file.
Usage: python _generic_audit.py <chassis|modules|reactors>
"""
import re, json, sys
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent

target = sys.argv[1] if len(sys.argv) > 1 else "chassis"
FILE_MAP = {
    "chassis":  "cybots_wiki/pages/Module/Chassis_data.wikitext",
    "modules":  "cybots_wiki/pages/Module/Modules_data.wikitext",
    "reactors": "cybots_wiki/pages/Module/Reactors_data.wikitext",
}
path = WORKSPACE / FILE_MAP[target]

catalog = json.load(open(WORKSPACE / "REFERENCES/knowledge/image_catalog.json"))
allimages_raw = json.load(open(WORKSPACE / "cybots_wiki/allimages.json"))["allimages"]
fandom = {img["name"].lower(): img["name"] for img in allimages_raw}

# Build name -> fandom filename (all depicts)
name_to_img = {}
for img_path, meta in catalog.items():
    src = img_path.split("/")[-1]
    fandom_file = fandom.get(src.lower())
    if not fandom_file:
        continue
    for name in meta.get("used_by", []):
        if name.lower() not in name_to_img:
            name_to_img[name.lower()] = fandom_file

text = path.read_text(encoding="utf-8")
entries = list(re.finditer(r'(?s)\n    \{\n        title = "([^"]+)"(.*?)(?=\n    \{|\n\}$)', text))

broken = []
adds   = []
fixes  = []
still_nil = []

for m in entries:
    title   = m.group(1)
    block   = m.group(0)
    img_m   = re.search(r'image1\s*=\s*"([^"]+)"', block)
    nil_m   = re.search(r'image1\s*=\s*nil', block)
    current = img_m.group(1) if img_m else None
    best    = name_to_img.get(title.lower())

    if current:
        if current.lower() not in fandom:
            broken.append((title, current, best))
        elif best and current.lower() != best.lower():
            fixes.append((title, current, best))
    elif nil_m:
        if best:
            adds.append((title, best))
        else:
            still_nil.append(title)

print(f"File: {FILE_MAP[target]}")
print(f"\n=== BROKEN ({len(broken)}) ===")
for t, cur, best in broken:
    hint = repr(best) if best else "[no match]"
    print(f"  {t!r:45} current={cur!r}  => {hint}")

print(f"\n=== TO FIX ({len(fixes)}) ===")
for t, cur, best in fixes:
    print(f"  {t!r:45} current={cur!r:30} => {best!r}")

print(f"\n=== TO ADD ({len(adds)}) ===")
for t, best in adds:
    print(f"  {t!r:45} => {best!r}")

print(f"\n=== STILL NIL ({len(still_nil)}) ===")
for t in still_nil:
    print(f"  {t!r}")
