"""
Catalog-based image audit for Enemies_data.
Uses image_catalog.json `used_by` to build name->fandom_image map,
then checks every entry (by title AND chassis name) and reports
what should be added or corrected.
"""
import re, json
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent

catalog   = json.load(open(WORKSPACE / "REFERENCES/knowledge/image_catalog.json"))
allimages_raw = json.load(open(WORKSPACE / "cybots_wiki/allimages.json"))["allimages"]
fandom    = {img["name"].lower(): img["name"] for img in allimages_raw}

# Build: name (lowercase) -> fandom filename
# For each catalog entry, all used_by names point to this image
name_to_img = {}   # used_by_name.lower() -> fandom filename
for path, meta in catalog.items():
    if meta.get("depicts") not in ("chassis", "enemy", "unit"):
        continue
    src_filename = path.split("/")[-1]  # e.g. "hover.png"
    fandom_file  = fandom.get(src_filename.lower())
    if not fandom_file:
        continue
    for name in meta.get("used_by", []):
        name_to_img[name.lower()] = fandom_file

print(f"Catalog chassis/enemy->image entries: {len(name_to_img)}")

# Parse Enemies_data line-by-line
enemies_path = WORKSPACE / "cybots_wiki/pages/Module/Enemies_data.wikitext"
text = enemies_path.read_text(encoding="utf-8")
entries = list(re.finditer(r'(?s)\n    \{\n        title = "([^"]+)"(.*?)(?=\n    \{|\n\}$)', text))

adds    = []
fixes   = []
missing = []

for m in entries:
    title   = m.group(1)
    block   = m.group(0)
    img_m   = re.search(r'image1\s*=\s*"([^"]+)"', block)
    ch_m    = re.search(r'chassis\s*=\s*\{\s*name\s*=\s*"([^"]+)"', block)
    chassis = ch_m.group(1) if ch_m else None
    current = img_m.group(1) if img_m else None

    # Look up by title first, then chassis
    best = (name_to_img.get(title.lower())
            or (chassis and name_to_img.get(chassis.lower())))

    if not best:
        if not current:
            missing.append(f"  NO_IMG  {title!r:40} chassis={chassis!r}")
    elif not current:
        adds.append((title, chassis, best))
    elif current.lower() != best.lower():
        fixes.append((title, current, best))

print(f"\n=== TO ADD ({len(adds)}) ===")
for t, c, b in adds:
    print(f"  {t!r:40} chassis={c!r:35} => {b!r}")

print(f"\n=== TO FIX ({len(fixes)}) ===")
for t, cur, new in fixes:
    print(f"  {t!r:40} current={cur!r:30} => {new!r}")

print(f"\n=== STILL UNRESOLVED ({len(missing)}) ===")
for s in missing:
    print(s)
