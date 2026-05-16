"""
Apply catalog-based image fixes to Chassis_data, Modules_data, Reactors_data.
For each entry: fix wrong values and fill nil values using catalog used_by lookup.
Broken images with no catalog match are set to nil.
"""
import re, json
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent

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


def fix_file(rel_path, broken_to_nil=None):
    """
    broken_to_nil: list of titles whose current image1 is broken and should become nil
    """
    broken_to_nil = set(broken_to_nil or [])
    path = WORKSPACE / rel_path
    text = path.read_text(encoding="utf-8")

    fixed = 0
    added = 0
    nulled = 0

    def replacer(m):
        nonlocal fixed, added, nulled
        title = m.group(1)
        block = m.group(0)
        img_m   = re.search(r'(        image1 = )"([^"]+)"', block)
        nil_m   = re.search(r'(        image1 = )nil', block)
        current = img_m.group(2) if img_m else None
        best    = name_to_img.get(title.lower())

        if title in broken_to_nil and current and current.lower() not in fandom:
            # broken image, no catalog match → null it
            new_block = block.replace(img_m.group(0), img_m.group(1) + 'nil', 1)
            nulled += 1
            return new_block

        if current:
            if best and current.lower() != best.lower() and current.lower() in fandom:
                # wrong image per catalog → fix
                new_block = block.replace(img_m.group(0), img_m.group(1) + f'"{best}"', 1)
                fixed += 1
                return new_block
        elif nil_m and best:
            # nil → fill from catalog
            new_block = block.replace(nil_m.group(0), nil_m.group(1) + f'"{best}"', 1)
            added += 1
            return new_block

        return block

    pattern = r'(?s)\n    \{\n        title = "([^"]+)"(.*?)(?=\n    \{|\n\}$)'
    new_text = re.sub(pattern, replacer, text)
    path.write_text(new_text, encoding="utf-8")
    print(f"{rel_path}: {fixed} fixed, {added} added, {nulled} nulled to nil")


fix_file("cybots_wiki/pages/Module/Chassis_data.wikitext")
fix_file("cybots_wiki/pages/Module/Modules_data.wikitext")
fix_file("cybots_wiki/pages/Module/Reactors_data.wikitext",
         broken_to_nil=["Hyper Syncron Core 2"])
