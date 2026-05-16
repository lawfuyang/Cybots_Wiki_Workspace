"""
Audit Weapons_data.wikitext:
1. Find image1 values that don't exist in allimages (broken)
2. Check catalog used_by for all depicts types to find better image matches
"""
import re, json
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent

catalog = json.load(open(WORKSPACE / "REFERENCES/knowledge/image_catalog.json"))
allimages_raw = json.load(open(WORKSPACE / "cybots_wiki/allimages.json"))["allimages"]
fandom = {img["name"].lower(): img["name"] for img in allimages_raw}

# Build: weapon title (lowercase) -> fandom filename (all depicts types)
name_to_img = {}
for path, meta in catalog.items():
    src = path.split("/")[-1]
    fandom_file = fandom.get(src.lower())
    if not fandom_file:
        continue
    for name in meta.get("used_by", []):
        if name.lower() not in name_to_img:
            name_to_img[name.lower()] = fandom_file

# Parse Weapons_data
weapons_path = WORKSPACE / "cybots_wiki/pages/Module/Weapons_data.wikitext"
text = weapons_path.read_text(encoding="utf-8")
entries = list(re.finditer(r'(?s)\n    \{\n        title = "([^"]+)"(.*?)(?=\n    \{|\n\}$)', text))

broken = []   # image1 set but file not in allimages
adds   = []   # image1 is nil, catalog has a match
fixes  = []   # image1 set but catalog says different
ok_nil = []   # image1 nil, no catalog match

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
            ok_nil.append(title)

print(f"=== BROKEN (image1 set but not in allimages) ({len(broken)}) ===")
for t, cur, best in broken:
    hint = f" => {best!r}" if best else " [no catalog match]"
    print(f"  {t!r:45} current={cur!r}{hint}")

print(f"\n=== TO FIX (catalog says different) ({len(fixes)}) ===")
for t, cur, best in fixes:
    print(f"  {t!r:45} current={cur!r:30} => {best!r}")

print(f"\n=== TO ADD (nil, catalog has match) ({len(adds)}) ===")
for t, best in adds:
    print(f"  {t!r:45} => {best!r}")

print(f"\n=== STILL NIL (no catalog match) ({len(ok_nil)}) ===")
for t in ok_nil:
    print(f"  {t!r}")
