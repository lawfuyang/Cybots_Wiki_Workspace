"""
Fix script for:
1. Modules_data.wikitext – fill in nil image1 values and correct wrong ones
2. Enemies_data.wikitext – remove all `url` entries and the local `url()` helper
"""

import re
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent

# ────────────────────────────────────────────────────────────
# 1. Modules_data – image assignments
# ────────────────────────────────────────────────────────────
# Map of entry title -> correct Fandom filename
MODULE_IMAGE_MAP = {
    # wrong non-nil values
    "Gravity Hydro Booster":        "Ghb.jpg",
    "Basewall Effect":              "Module_armour.jpg",
    "prometeus module":             "Prometeus.jpg",
    # nil → Module3.jpg  (combat/offensive modules per catalog)
    "EM Repulsor Field":            "Module3.jpg",
    "Voltage Conveyer":             "Module3.jpg",
    "Omega Pathfinder":             "Module3.jpg",
    "Enhanced Optics":              "Module3.jpg",
    "Gunnery Metalink":             "Module3.jpg",
    "Threat Analyser":              "Module3.jpg",
    "Damage Control":               "Module3.jpg",
    "Multiphase Syncroniser":       "Module3.jpg",
    "Linked Fire Control":          "Module3.jpg",
    # nil → Module_armour.jpg  (armour/wall modules per catalog)
    "Armour":                       "Module_armour.jpg",
    "Sloped Armour":                "Module_armour.jpg",
    "Reinforced Hull":              "Module_armour.jpg",
    "Reactive Armour":              "Module_armour.jpg",
    "Medium Wall Effect":           "Module_armour.jpg",
    "Heavy Wall Effect":            "Module_armour.jpg",
    "Light Wall Effect":            "Module_armour.jpg",
    "High Ground":                  "Module_armour.jpg",
    # nil → Brain.jpg  (tactical/mastery modules per catalog)
    "Tactical Genius":              "Brain.jpg",
    "Inspiration":                  "Inspiration.jpg",
    # nil → Horus rune images (catalog rune1–4)
    "Horus Fire of Ra":             "Fieryrune.jpg",
    "Horus moon of Ra":             "Lunarrune.jpg",
    "Horus Ice of Ra":              "Icyrune.jpg",
    "Horus Sun of Ra":              "Solarrune.jpg",
}

modules_path = WORKSPACE / "cybots_wiki/pages/Module/Modules_data.wikitext"
lines = modules_path.read_text(encoding="utf-8").splitlines(keepends=True)

TITLE_RE   = re.compile(r'^\s+title = "([^"]+)"')
IMAGE1_STR = re.compile(r'^(\s+image1 = )"([^"]+)"(,?\s*$)')
IMAGE1_NIL = re.compile(r'^(\s+image1 = )nil(,?\s*$)')

new_lines  = []
cur_title  = None
changed    = 0

for line in lines:
    t = TITLE_RE.match(line)
    if t:
        cur_title = t.group(1)

    target = MODULE_IMAGE_MAP.get(cur_title)
    if target:
        # Replace existing string value
        m = IMAGE1_STR.match(line)
        if m:
            new_lines.append(f'{m.group(1)}"{target}"{m.group(3)}')
            print(f"  FIX  [{cur_title}] {m.group(2)!r} -> {target!r}")
            changed += 1
            continue
        # Replace nil value
        m = IMAGE1_NIL.match(line)
        if m:
            new_lines.append(f'{m.group(1)}"{target}"{m.group(2)}')
            print(f"  ADD  [{cur_title}] nil -> {target!r}")
            changed += 1
            continue

    new_lines.append(line)

modules_path.write_text("".join(new_lines), encoding="utf-8")
print(f"\n  => Wrote {changed} changes to Modules_data.wikitext\n")


# ────────────────────────────────────────────────────────────
# 2. Enemies_data – remove url entries and url() helper
# ────────────────────────────────────────────────────────────
enemies_path = WORKSPACE / "cybots_wiki/pages/Module/Enemies_data.wikitext"
text = enemies_path.read_text(encoding="utf-8")

# Step A: remove the `local function url(name)...end` block (+ trailing blank line)
text = re.sub(
    r'\nlocal function url\(name\)\n.*?end\n\n',
    '\n',
    text,
    flags=re.DOTALL
)

# Step B: remove top-level `url = url("...")` lines (8-space indent)
text = re.sub(r'^        url = url\("[^"]*"\),\n', '', text, flags=re.MULTILINE)

# Step C: remove `, url = url("...")` inside inline tables
# Use "[^"]+" to avoid stopping at parens inside the argument string
text = re.sub(r',\s*url = url\("[^"]*"\)', '', text)

enemies_path.write_text(text, encoding="utf-8")
print("  => Cleaned Enemies_data.wikitext (removed url helper + all url entries)")
