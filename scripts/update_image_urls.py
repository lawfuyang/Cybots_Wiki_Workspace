"""
Script to update image1 fields in Lua data modules to match actual Fandom file names.

Strategy:
1. Build a lookup of all fandom images (case-insensitive key -> actual name)
2. Build a reverse catalog: item_name (lowercase) -> fandom filename
3. For each wikitext file with existing image1 fields (Chassis, Weapons, Modules, Reactors, Shields):
   - For existing image1 values: try direct case-insensitive match first
   - If no match: try via catalog's used_by (match on entry title)
   - If still no match: try stem-only match (ignore extension difference)
4. For Enemies_data: add image1 based on chassis/title lookup in catalog
5. Write updated files and report all changes
"""

import json
import re
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent

# ── Load data ──────────────────────────────────────────────────────────────────

with open(WORKSPACE / "cybots_wiki/allimages.json") as f:
    allimages_data = json.load(f)

with open(WORKSPACE / "REFERENCES/knowledge/image_catalog.json") as f:
    catalog = json.load(f)

# Maps lowercase filename -> actual Fandom filename (preserving original case)
fandom_images: dict[str, str] = {
    img["name"].lower(): img["name"] for img in allimages_data["allimages"]
}

# Build reverse catalog: lowercase item name -> list of candidate fandom filenames
# Walk every catalog entry: game_path -> { used_by: [...] }
# If the game filename matches a Fandom file, map each used_by name -> that Fandom file
item_to_fandom: dict[str, list[str]] = {}
for game_path, entry in catalog.items():
    src_filename = game_path.split("/")[-1]   # e.g. "argonlaser.jpg"
    fandom_match = fandom_images.get(src_filename.lower())
    if not fandom_match:
        continue
    for used_by_name in entry.get("used_by", []):
        key = used_by_name.lower()
        if key not in item_to_fandom:
            item_to_fandom[key] = []
        if fandom_match not in item_to_fandom[key]:
            item_to_fandom[key].append(fandom_match)


# ── Helpers ────────────────────────────────────────────────────────────────────

def levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for ca in a:
        curr = [prev[0] + 1]
        for j, cb in enumerate(b):
            curr.append(min(prev[j + 1] + 1, curr[j] + 1, prev[j] + (ca != cb)))
        prev = curr
    return prev[len(b)]


def resolve_image(current_image: str, entry_title: str) -> tuple[str, str]:
    """
    Returns (resolved_filename, method):
      'unchanged'  - already correct
      'case_fix'   - corrected capitalisation
      'catalog'    - matched via catalog used_by
      'stem'       - matched by filename stem (extension differed)
      'no_match'   - could not find a Fandom file
    """
    # 1. Direct case-insensitive match
    direct = fandom_images.get(current_image.lower())
    if direct:
        if direct == current_image:
            return current_image, "unchanged"
        return direct, "case_fix"

    # 2. Catalog used_by lookup using entry title
    candidates = item_to_fandom.get(entry_title.lower(), [])
    if len(candidates) == 1:
        return candidates[0], "catalog"
    if len(candidates) > 1:
        current_stem = current_image.lower().rsplit(".", 1)[0]
        best = min(candidates, key=lambda c: levenshtein(c.lower().rsplit(".", 1)[0], current_stem))
        return best, f"catalog_ambiguous({len(candidates)})"

    # 3. Stem-only match (extension might differ, e.g. .jpg vs .png)
    current_stem = current_image.lower().rsplit(".", 1)[0]
    stem_matches = [name for lower, name in fandom_images.items()
                    if lower.rsplit(".", 1)[0] == current_stem]
    if len(stem_matches) == 1:
        return stem_matches[0], "stem"

    # 4. Replace spaces with underscores and retry
    underscored = current_image.replace(" ", "_")
    if underscored != current_image:
        direct = fandom_images.get(underscored.lower())
        if direct:
            return direct, "space_fix"

    return current_image, "no_match"


def find_image_for_item(item_name: str) -> tuple[str | None, str]:
    """Find a Fandom image for a named item (enemy title or chassis name)."""
    candidates = item_to_fandom.get(item_name.lower(), [])
    if len(candidates) == 1:
        return candidates[0], "catalog_direct"
    if len(candidates) > 1:
        return candidates[0], f"catalog_ambiguous({len(candidates)})"

    # Direct file lookup: try "<itemname_nospaces>.jpg/.png"
    slug = item_name.lower().replace(" ", "")
    for ext in ("jpg", "png"):
        direct = fandom_images.get(f"{slug}.{ext}")
        if direct:
            return direct, "slug_direct"

    return None, "no_match"


# ── Process files with existing image1 fields ─────────────────────────────────

IMAGE1_RE = re.compile(r'^( +image1 = ")([^"]+)(")')
TITLE_RE  = re.compile(r'^\s+title = "([^"]+)"')

DATA_FILES = [
    "cybots_wiki/pages/Module/Chassis_data.wikitext",
    "cybots_wiki/pages/Module/Modules_data.wikitext",
    "cybots_wiki/pages/Module/Reactors_data.wikitext",
    "cybots_wiki/pages/Module/Shields_data.wikitext",
    "cybots_wiki/pages/Module/Weapons_data.wikitext",
]

total_changed   = 0
total_unchanged = 0
total_no_match  = 0

for rel_path in DATA_FILES:
    filepath = WORKSPACE / rel_path
    lines    = filepath.read_text(encoding="utf-8").splitlines(keepends=True)

    changed_count = 0
    new_lines     = []
    current_title = None

    for line in lines:
        t_match = TITLE_RE.match(line)
        if t_match:
            current_title = t_match.group(1)

        img_match = IMAGE1_RE.match(line)
        if img_match:
            prefix, current_img, suffix = img_match.group(1), img_match.group(2), img_match.group(3)
            resolved, method = resolve_image(current_img, current_title or "")

            if method == "unchanged":
                total_unchanged += 1
                new_lines.append(line)
            elif method == "no_match":
                total_no_match += 1
                print(f"  NO MATCH  [{current_title}] image1={current_img!r}")
                new_lines.append(line)
            else:
                total_changed += 1
                changed_count += 1
                rest = line[img_match.end():]   # trailing newline / comment
                new_lines.append(f'{prefix}{resolved}{suffix}{rest}')
                print(f"  UPDATED   [{current_title}] {current_img!r} -> {resolved!r}  ({method})")
        else:
            new_lines.append(line)

    if changed_count > 0:
        filepath.write_text("".join(new_lines), encoding="utf-8")
        print(f"  => Wrote {changed_count} changes to {rel_path}\n")
    else:
        print(f"  => No changes for {rel_path}\n")

# ── Process Enemies_data.wikitext (add image1 after url line) ─────────────────
#
# Enemy entry format (8-space indent for top-level fields):
#   {
#       title   = "Flea",
#       url     = url("Flea"),            <- insert image1 AFTER this line
#       chassis = { name = "Ranger", ... },
#       ...
#   },
#
# Top-level url is at exactly 8 spaces; nested urls (inside weapons/shields) are
# at 12 spaces, so we can distinguish them by indentation.

ENEMY_TITLE_RE   = re.compile(r'^        title = "([^"]+)"')
ENEMY_CHASSIS_RE = re.compile(r'^        chassis = \{ name = "([^"]+)"')
TOP_LEVEL_URL_RE = re.compile(r'^        url = url\(')   # exactly 8 spaces
IMAGE1_EXISTING  = re.compile(r'^        image1 = ')

enemies_path  = WORKSPACE / "cybots_wiki/pages/Module/Enemies_data.wikitext"
enemies_lines = enemies_path.read_text(encoding="utf-8").splitlines(keepends=True)

# First pass: collect per-entry metadata so we can resolve images before rewriting.
# Each entry: { line_of_url: int, title: str, chassis: str|None }
entries: list[dict] = []
cur_entry: dict | None = None

for idx, line in enumerate(enemies_lines):
    t = ENEMY_TITLE_RE.match(line)
    if t:
        cur_entry = {"title": t.group(1), "chassis": None, "url_line": None, "has_image1": False}
        entries.append(cur_entry)
        continue
    if cur_entry is None:
        continue
    if TOP_LEVEL_URL_RE.match(line):
        if cur_entry["url_line"] is None:
            cur_entry["url_line"] = idx
    c = ENEMY_CHASSIS_RE.match(line)
    if c:
        cur_entry["chassis"] = c.group(1)
    if IMAGE1_EXISTING.match(line):
        cur_entry["has_image1"] = True

# Second pass: build insertion map { line_index: image1_line_to_insert }
insertions: dict[int, str] = {}
enemy_changed = 0
for entry in entries:
    if entry["has_image1"]:
        continue   # already has image1 – skip
    if entry["url_line"] is None:
        continue

    title   = entry["title"]
    chassis = entry["chassis"]
    img, method = find_image_for_item(title)
    if not img and chassis:
        img, method = find_image_for_item(chassis)

    if img:
        insertions[entry["url_line"]] = f'        image1 = "{img}",\n'
        enemy_changed += 1
        print(f"  ENEMY ADD [{title}] (chassis={chassis}) -> {img!r}  ({method})")
    else:
        print(f"  ENEMY SKIP [{title}] (chassis={chassis}) - no image found")

# Third pass: write file with insertions
if insertions:
    new_lines = []
    for idx, line in enumerate(enemies_lines):
        new_lines.append(line)
        if idx in insertions:
            new_lines.append(insertions[idx])
    enemies_path.write_text("".join(new_lines), encoding="utf-8")
    print(f"\n  => Wrote {enemy_changed} image1 entries to Enemies_data.wikitext")
else:
    print("\n  => No image1 entries added to Enemies_data.wikitext")

# ── Summary ────────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"Summary:")
print(f"  Already correct (unchanged):  {total_unchanged}")
print(f"  Updated (case / catalog / stem): {total_changed}")
print(f"  No match found:                  {total_no_match}")
print(f"  Enemy image1 entries added:      {enemy_changed}")
