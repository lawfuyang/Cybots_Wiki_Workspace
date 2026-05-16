#!/usr/bin/env python3
"""
sync_wiki_data.py - Comprehensive sync of cache JSON data to wiki Lua data modules.

Runs all six data modules (Weapons, Modules, Reactors, Shields, Chassis, Enemies):
  1. Updates incorrect field values in existing entries
  2. Adds entirely missing entries (weapons/modules/reactors/shields/enemies)
  3. Updates image1 fields via image_catalog.json + allimages.json lookup

Usage:
    python scripts/sync_wiki_data.py [--dry-run] [--type weapons|modules|reactors|shields|chassis|enemies]

If no --type is given, all six data modules are processed.
"""

import json
import re
import sys
import argparse
from pathlib import Path

# â”€â”€â”€ Paths â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

WORKSPACE  = Path(__file__).parent.parent
REFS       = WORKSPACE / "REFERENCES"
WIKI_DIR   = WORKSPACE / "cybots_wiki" / "pages" / "Module"

WIKI_FILES = {
    "weapons":  WIKI_DIR / "Weapons_data.wikitext",
    "modules":  WIKI_DIR / "Modules_data.wikitext",
    "reactors": WIKI_DIR / "Reactors_data.wikitext",
    "shields":  WIKI_DIR / "Shields_data.wikitext",
    "chassis":  WIKI_DIR / "Chassis_data.wikitext",
    "enemies":  WIKI_DIR / "Enemies_data.wikitext",
}

CACHE_FILES = {
    "weapons":  REFS / "weapons_cache.json",
    "modules":  REFS / "modules_cache.json",
    "reactors": REFS / "reactors_cache.json",
    "shields":  REFS / "shields_cache.json",
    "chassis":  REFS / "chassis_cache.json",
    "enemies":  REFS / "enemies_cache.json",
}

# â”€â”€â”€ Name normalisation tables â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Maps cache key â†’ canonical wiki title (for items whose names differ)

CACHE_TO_WIKI_TITLE = {
    # Weapons (cache uses older or abbreviated names)
    "Shield Disrupter":      "Shield Disruptor",
    "Adv. Cyclic Laser":     "Advanced Cyclic Laser",
    # Shields with disambiguation suffix in wiki
    "Baron":                 "Baron (Shield)",
    "Argon":                 "Argon (Shield)",
    "Plasma":                "Plasma (Shield)",
    # Shields: minor case differences
    "SXD10":                 "SxD10",
    # Reactors: spacing difference
    "Magtronic Powercell":   "Magtronic Power Cell",
    # Modules: wiki drops "Module" suffix or changes capitalisation
    "Hyper Drive Module":    "Hyper Drive",
    "Plutonium Core Module": "Plutonium Core",
    "basewall Effect":       "Basewall Effect",
    # Chassis: cache uses lowercase-first for some internal keys
    "cyBulwark":             "CyBulwark",
    # Enemies: typos in cache
    "Scaen Grenadiers":      "Scaven Grenadiers",
}

# Reverse mapping: wiki title â†’ cache key (built automatically)
WIKI_TO_CACHE_KEY: dict[str, str] = {v: k for k, v in CACHE_TO_WIKI_TITLE.items()}


def cache_key_for_wiki_title(title: str, cache: dict) -> str | None:
    """Return the cache key that corresponds to a wiki title, or None."""
    if title in cache:
        return title
    mapped = WIKI_TO_CACHE_KEY.get(title)
    if mapped and mapped in cache:
        return mapped
    # Case-insensitive fallback
    title_lo = title.lower()
    for k in cache:
        if k.lower() == title_lo:
            return k
    return None


# â”€â”€â”€ Lua entry extraction â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def extract_lua_entries(content: str) -> dict[str, tuple[str, int, int]]:
    """
    Return {title: (entry_text, start, end)} for every top-level entry
    in the Lua array literal (entries are delimited by outer braces).
    """
    entries: dict[str, tuple[str, int, int]] = {}
    title_pat = re.compile(r'title\s*=\s*"([^"]+)"')
    for m in title_pat.finditer(content):
        title     = m.group(1)
        pos       = m.start()
        # Walk backward to find the opening '{' of this entry
        entry_start = pos
        for i in range(pos - 1, -1, -1):
            if content[i] == '{':
                entry_start = i
                break
        # Walk forward to find the matching '}'
        depth     = 0
        entry_end = entry_start
        for i in range(entry_start, len(content)):
            if content[i] == '{':
                depth += 1
            elif content[i] == '}':
                depth -= 1
                if depth == 0:
                    entry_end = i + 1
                    break
        entries[title] = (content[entry_start:entry_end], entry_start, entry_end)
    return entries


# â”€â”€â”€ Section value reading â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_SCALAR_PAT = re.compile(
    r'(?:'
    r'nil'
    r'|"[^"]*"'
    r'|[-]?\d+(?:\.\d+)?'
    r'|\{\s*value\s*=\s*([-]?\d+(?:\.\d+)?)\s*,\s*unit\s*=\s*"[^"]*"\s*\}'
    r')',
    re.DOTALL,
)


def _get_section_text(entry_text: str, section: str) -> str | None:
    pat = re.compile(r'\["' + re.escape(section) + r'"\]\s*=\s*\{', re.DOTALL)
    sm = pat.search(entry_text)
    if not sm:
        return None
    start = sm.end() - 1
    depth = 0
    end   = start
    for i in range(start, len(entry_text)):
        if entry_text[i] == '{':
            depth += 1
        elif entry_text[i] == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    return entry_text[start:end]


def get_section_value(entry_text: str, section: str, field: str):
    """Read the value of `field` inside `section`.  Returns Python int/float/str/None."""
    sec = _get_section_text(entry_text, section)
    if sec is None:
        return None
    field_pat = re.compile(
        r'\["' + re.escape(field) + r'"\]\s*=\s*('
        r'nil'
        r'|"[^"]*"'
        r'|[-]?\d+(?:\.\d+)?'
        r'|\{\s*value\s*=\s*([-]?\d+(?:\.\d+)?)\s*,\s*unit\s*=\s*"[^"]*"\s*\}'
        r')',
        re.DOTALL,
    )
    fm = field_pat.search(sec)
    if not fm:
        return None
    raw = fm.group(1).strip()
    if raw == 'nil':
        return None
    if raw.startswith('"'):
        return raw.strip('"')
    if raw.startswith('{'):
        # { value = X, unit = "%" }
        vm = re.search(r'value\s*=\s*([-]?\d+(?:\.\d+)?)', raw)
        if vm:
            v = vm.group(1)
            return float(v) if '.' in v else int(v)
        return raw
    v = raw
    return float(v) if '.' in v else int(v)


def get_top_level_value(entry_text: str, field: str):
    """Read a top-level scalar field (e.g. image1)."""
    pat = re.compile(r'\b' + re.escape(field) + r'\s*=\s*(nil|"[^"]*"|[-]?\d+(?:\.\d+)?)', re.DOTALL)
    m = pat.search(entry_text)
    if not m:
        return None
    raw = m.group(1).strip()
    if raw == 'nil':
        return None
    if raw.startswith('"'):
        return raw.strip('"')
    return float(raw) if '.' in raw else int(raw)


# â”€â”€â”€ Value formatting â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def fmt_lua(value, is_percent: bool = False, force_float: bool = False) -> str:
    """Format a Python value as a Lua literal."""
    if value is None:
        return 'nil'
    if is_percent:
        pct = round(value * 100)
        return f'{{ value = {pct}, unit = "%" }}'
    if isinstance(value, float):
        if value == int(value) and not force_float:
            return str(int(value))
        return str(value)
    return str(value)


def values_equal(wiki_val, cache_val, is_percent: bool = False) -> bool:
    """True if both represent the same effective value."""
    if wiki_val is None and cache_val is None:
        return True
    if wiki_val is None or cache_val is None:
        return False
    try:
        w = float(wiki_val)
        c = float(cache_val) * 100 if is_percent else float(cache_val)
        return abs(w - c) < 0.0001
    except (TypeError, ValueError):
        return str(wiki_val).strip().lower() == str(cache_val).strip().lower()


# â”€â”€â”€ Section value replacement â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def set_section_value(entry_text: str, section: str, field: str, new_lua: str) -> str:
    """
    Replace the value of `field` inside `section` within `entry_text`.
    Handles nil, numbers, and { value=â€¦, unit=â€¦ } forms.
    Returns the updated entry_text (unchanged if field not found).
    """
    sec_text = _get_section_text(entry_text, section)
    if sec_text is None:
        return entry_text

    field_re = re.compile(
        r'(\["' + re.escape(field) + r'"\]\s*=\s*)'
        r'(?:nil|"[^"]*"|[-]?\d+(?:\.\d+)?|\{[^}]*\})',
        re.DOTALL,
    )
    new_sec = field_re.sub(lambda m: m.group(1) + new_lua, sec_text, count=1)
    if new_sec == sec_text:
        return entry_text  # field not found / no change

    # Find where sec_text starts in entry_text and replace
    idx = entry_text.find(sec_text)
    if idx == -1:
        return entry_text
    return entry_text[:idx] + new_sec + entry_text[idx + len(sec_text):]


def set_top_level_value(entry_text: str, field: str, new_lua: str) -> str:
    """Replace a top-level scalar field (e.g. image1)."""
    pat = re.compile(
        r'(\b' + re.escape(field) + r'\s*=\s*)'
        r'(?:nil|"[^"]*"|[-]?\d+(?:\.\d+)?)',
        re.DOTALL,
    )
    result, n = pat.subn(lambda m: m.group(1) + new_lua, entry_text, count=1)
    if n == 0:
        # Field missing entirely â€” insert after the title line
        title_m = re.search(r'(title\s*=\s*"[^"]*",\n)', entry_text)
        if title_m:
            ins = title_m.end()
            result = entry_text[:ins] + f'        {field} = {new_lua},\n' + entry_text[ins:]
    return result


# â”€â”€â”€ Image resolution â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def build_image_index(catalog: dict, allimages: list[dict]) -> tuple[dict, dict]:
    """
    Returns:
      fandom_images  : {lowercase_filename: actual_filename}
      item_to_fandom : {lowercase_item_name: actual_filename}
    """
    fandom_images = {img["name"].lower(): img["name"] for img in allimages}
    item_to_fandom: dict[str, str] = {}
    for img_path, meta in catalog.items():
        src  = img_path.split("/")[-1]
        fname = fandom_images.get(src.lower())
        if not fname:
            continue
        for name in meta.get("used_by", []):
            if name.lower() not in item_to_fandom:
                item_to_fandom[name.lower()] = fname
    return fandom_images, item_to_fandom


def resolve_image(title: str, item_to_fandom: dict, fandom_images: dict) -> str | None:
    """Return the best Fandom filename for `title`, or None if not found."""
    lo = title.lower()
    # Direct name match in catalog
    if lo in item_to_fandom:
        return item_to_fandom[lo]
    # Slug match (title without spaces/special chars)
    slug = re.sub(r'[^a-z0-9]', '', lo)
    for key, fname in fandom_images.items():
        if re.sub(r'[^a-z0-9]', '', key.rsplit('.', 1)[0]) == slug:
            return fname
    return None


# â”€â”€â”€ Field maps per data type â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Each entry: (section, wiki_field, cache_key, is_percent)

WEAPONS_FIELDS = [
    ("Properties", "Offensive Merit",    "merit",          False),
    ("Properties", "Shield Damage",      "shield_damage",  False),
    ("Properties", "Armor Piercing",     "armor_damage",   False),
    ("Properties", "Energy Drain",       "energy_drain",   False),
    ("Properties", "Damage Radius",      "damage_radius",  False),
    ("Properties", "Shots Per Turn",     "shots_per_turn", False),
    ("Properties", "Energy Per Shot",    "energy_per_shot",False),
    ("Properties", "Accuracy",           "accuracy",       False),
    ("Properties", "Required Tech Level","tech_level",     False),
    ("Properties", "Weight",             "weight",         False),
]

MODULES_FIELDS = [
    ("Properties", "Defensive Merit",      "merit",                  False),
    ("Properties", "Energy Use",           "energy_use",             False),
    ("Properties", "Required Tech Level",  "tech_level",             False),
    ("Properties", "Weight",               "weight",                 False),
    ("Properties", "Critical Hit Chance",  "critical_hit_chance",    True),
    ("Properties", "Accuracy",             "accuracy_boost",         True),
    ("Properties", "Speed",                "speed",                  True),
    ("Properties", "Firing Rate",          "firing_rate",            True),
    ("Properties", "Shield Deflection",    "shield_deflection",      True),
    ("Properties", "Armor Deflection",     "armor_deflection",       True),
    ("Properties", "Energy Drain Deflection","energy_drain_deflection",True),
]

REACTORS_FIELDS = [
    ("Unit Information", "Required Tech Level", "tech_level",    False),
    ("Unit Information", "Weight",              "weight",        False),
    ("Properties",       "Max Energy Level",    "max_power",     False),
    ("Properties",       "Recharge Rate",       "recharge_rate", False),
    ("Properties",       "Defensive Merit",     "merit",         False),
]

SHIELDS_FIELDS = [
    ("Unit Information", "Required Tech Level", "tech_level",    False),
    ("Unit Information", "Weight",              "weight",        False),
    ("Properties",       "Primary Level",       "primary_level", False),
    ("Properties",       "Energy Use",          "energy_use",    False),
    ("Properties",       "Recharge Rate",       "recharge_rate", False),
    ("Properties",       "Defensive Merit",     "merit",         False),
]

CHASSIS_FIELDS = [
    ("Slots",                "Weapon Slots",  "weapon_slots",        False),
    ("Slots",                "Shield Slots",  "shield_slots",        False),
    ("Slots",                "Module Slots",  "module_slots",        False),
    ("Base Stats",           "Armor",         "armor",               False),
    ("Base Stats",           "Speed",         "speed",               False),
    ("Base Stats",           "Payload",       "payload",             False),
    ("Base Stats",           "Critical Hit Chance","critical_hit_chance",True),
    ("Base Stats",           "Damage Adjusted","damage_boost",       True),
    ("Base Stats",           "Accuracy Adjusted","accuracy_boost",   True),
    ("Starting Tech Levels", "Weapon Tech",   "starting_weapon_tl",  False),
    ("Starting Tech Levels", "Shield Tech",   "starting_shield_tl",  False),
    ("Starting Tech Levels", "Reactor Tech",  "starting_reactor_tl", False),
    ("Starting Tech Levels", "Module Tech",   "starting_module_tl",  False),
    ("Unique Stats",         "Shield Projection","shield_projection", True),
    ("Unique Stats",         "Module Uplink", "module_uplink",       True),
    ("Hidden Stats",         "Drain Boost",   "drain_boost",         True),
]


# â”€â”€â”€ New entry generation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _wiki_url(title: str) -> str:
    safe = title.replace(' ', '_')
    return f"https://cybots.fandom.com/wiki/{safe}"


def _img_line(img: str | None) -> str:
    return f'"{img}"' if img else 'nil'


def gen_weapon_entry(title: str, d: dict, img: str | None) -> str:
    return (
        f'    {{\n'
        f'        title = "{title}",\n'
        f'        url = "{_wiki_url(title)}",\n'
        f'        image1 = {_img_line(img)},\n'
        f'        sections = {{\n'
        f'            ["Unit Information"] = {{\n'
        f'                ["Cost"] = nil,\n'
        f'                ["Weapon Type"] = nil,\n'
        f'                ["Other Requirements"] = "none",\n'
        f'            }},\n'
        f'            ["Properties"] = {{\n'
        f'                ["Weight"] = {d.get("weight") or "nil"},\n'
        f'                ["Required Tech Level"] = {d.get("tech_level") or "nil"},\n'
        f'                ["Shield Damage"] = {d.get("shield_damage") or "nil"},\n'
        f'                ["Armor Piercing"] = {d.get("armor_damage") or "nil"},\n'
        f'                ["Energy Drain"] = {d.get("energy_drain") or "nil"},\n'
        f'                ["Damage Radius"] = {d.get("damage_radius", "nil")},\n'
        f'                ["Accuracy"] = {d.get("accuracy") or "nil"},\n'
        f'                ["Shots Per Turn"] = {d.get("shots_per_turn") or "nil"},\n'
        f'                ["Energy Per Shot"] = {d.get("energy_per_shot") or "nil"},\n'
        f'                ["Max Targets Per Turn"] = nil,\n'
        f'                ["Offensive Merit"] = {d.get("merit") or "nil"},\n'
        f'            }},\n'
        f'        }},\n'
        f'    }},'
    )


def gen_module_entry(title: str, d: dict, img: str | None) -> str:
    def pct(v):
        if v is None:
            return 'nil'
        return f'{{ value = {round(v * 100)}, unit = "%" }}'
    return (
        f'    {{\n'
        f'        title = "{title}",\n'
        f'        url = "{_wiki_url(title)}",\n'
        f'        image1 = {_img_line(img)},\n'
        f'        sections = {{\n'
        f'            ["Unit Information"] = {{\n'
        f'                ["Cost"] = nil,\n'
        f'                ["Module Type"] = nil,\n'
        f'                ["Other Requirements"] = "none",\n'
        f'            }},\n'
        f'            ["Properties"] = {{\n'
        f'                ["Weight"] = {d.get("weight") or "nil"},\n'
        f'                ["Required Tech Level"] = {d.get("tech_level") or "nil"},\n'
        f'                ["Energy Use"] = {d.get("energy_use") or "nil"},\n'
        f'                ["Speed"] = {pct(d.get("speed"))},\n'
        f'                ["Critical Hit Chance"] = {pct(d.get("critical_hit_chance"))},\n'
        f'                ["Accuracy"] = {pct(d.get("accuracy_boost"))},\n'
        f'                ["Firing Rate"] = {pct(d.get("firing_rate"))},\n'
        f'                ["Shield Deflection"] = {pct(d.get("shield_deflection"))},\n'
        f'                ["Armor Deflection"] = {pct(d.get("armor_deflection"))},\n'
        f'                ["Energy Efficiency"] = nil,\n'
        f'                ["Energy Drain Deflection"] = {pct(d.get("energy_drain_deflection"))},\n'
        f'                ["Bounty Enhanced"] = nil,\n'
        f'                ["Experience Enhanced"] = nil,\n'
        f'                ["Defensive Merit"] = {d.get("merit") or "nil"},\n'
        f'            }},\n'
        f'        }},\n'
        f'    }},'
    )


def gen_reactor_entry(title: str, d: dict, img: str | None) -> str:
    return (
        f'    {{\n'
        f'        title = "{title}",\n'
        f'        url = "{_wiki_url(title)}",\n'
        f'        image1 = {_img_line(img)},\n'
        f'        sections = {{\n'
        f'            ["Unit Information"] = {{\n'
        f'                ["Cost"] = nil,\n'
        f'                ["Weight"] = {d.get("weight") or "nil"},\n'
        f'                ["Required Tech Level"] = {d.get("tech_level") or "nil"},\n'
        f'                ["Other Requirements"] = "none",\n'
        f'            }},\n'
        f'            ["Properties"] = {{\n'
        f'                ["Max Energy Level"] = {d.get("max_power") or "nil"},\n'
        f'                ["Recharge Rate"] = {d.get("recharge_rate") or "nil"},\n'
        f'                ["Defensive Merit"] = {d.get("merit") or "nil"},\n'
        f'            }},\n'
        f'        }},\n'
        f'    }},'
    )


def gen_shield_entry(title: str, d: dict, img: str | None) -> str:
    return (
        f'    {{\n'
        f'        title = "{title}",\n'
        f'        url = "{_wiki_url(title)}",\n'
        f'        image1 = {_img_line(img)},\n'
        f'        sections = {{\n'
        f'            ["Unit Information"] = {{\n'
        f'                ["Cost"] = nil,\n'
        f'                ["Weight"] = {d.get("weight") or "nil"},\n'
        f'                ["Required Tech Level"] = {d.get("tech_level") or "nil"},\n'
        f'                ["Other Requirements"] = "none",\n'
        f'            }},\n'
        f'            ["Properties"] = {{\n'
        f'                ["Primary Level"] = {d.get("primary_level") or "nil"},\n'
        f'                ["Energy Use"] = {d.get("energy_use") or "nil"},\n'
        f'                ["Recharge Rate"] = {d.get("recharge_rate") or "nil"},\n'
        f'                ["Defensive Merit"] = {d.get("merit") or "nil"},\n'
        f'            }},\n'
        f'        }},\n'
        f'    }},'
    )


def _item_list(items: list) -> str:
    """Format a shields/weapons/modules list for enemies."""
    if not items:
        return '{}'
    lines = [f'            {{ name = "{item}" }},' for item in items]
    return '{\n' + '\n'.join(lines) + '\n        }'


def gen_enemy_entry(title: str, d: dict, img: str | None) -> str:
    reactor = d.get("reactor")
    reactor_lua = f'{{ name = "{reactor}" }}' if reactor else 'nil'
    shields_lua = _item_list(d.get("shields") or [])
    weapons_lua = _item_list(d.get("weapons") or [])
    modules_lua = _item_list(d.get("modules") or [])
    chassis = d.get("chassis", "")
    return (
        f'    {{\n'
        f'        title = "{title}",\n'
        f'        image1 = {_img_line(img)},\n'
        f'        chassis = {{ name = "{chassis}" }},\n'
        f'        reactor = {reactor_lua},\n'
        f'        shields = {shields_lua},\n'
        f'        weapons = {weapons_lua},\n'
        f'        modules = {modules_lua},\n'
        f'    }},'
    )


# â”€â”€â”€ Enemy loadout updater â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _parse_name_list(block: str, field: str) -> list[str]:
    """Extract list of name strings from a { { name = "X" }, ... } field."""
    # Find the field
    pat = re.compile(r'\b' + re.escape(field) + r'\s*=\s*\{(.*?)\}', re.DOTALL)
    m = pat.search(block)
    if not m:
        return []
    inner = m.group(1)
    return re.findall(r'name\s*=\s*"([^"]+)"', inner)


def update_enemy_loadout(entry_text: str, d: dict) -> str:
    """Replace chassis/reactor/shields/weapons/modules in an existing enemy entry."""
    result = entry_text

    # chassis
    chassis = d.get("chassis", "")
    result = re.sub(
        r'(chassis\s*=\s*\{\s*name\s*=\s*)"[^"]*"',
        rf'\g<1>"{chassis}"',
        result, count=1,
    )

    # reactor
    reactor = d.get("reactor")
    if reactor:
        new_reactor = f'{{ name = "{reactor}" }}'
    else:
        new_reactor = 'nil'
    result = re.sub(
        r'reactor\s*=\s*(?:nil|\{[^}]*\})',
        f'reactor = {new_reactor}',
        result, count=1,
    )

    # shields / weapons / modules â€” replace complete list blocks
    for field_name, cache_key in [("shields", "shields"), ("weapons", "weapons"), ("modules", "modules")]:
        items = d.get(cache_key) or []
        new_list = _item_list(items)
        # Match:  shields = { ... }  (possibly multi-line, possibly empty {})
        list_pat = re.compile(
            r'(' + re.escape(field_name) + r'\s*=\s*)\{[^}]*\}',
            re.DOTALL,
        )
        result = list_pat.sub(lambda m, nl=new_list: m.group(1) + nl, result, count=1)

    return result


# â”€â”€â”€ Per-type processing â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def process_stats_file(
    data_type: str,
    cache: dict,
    content: str,
    field_map: list,
    gen_entry_fn,
    item_to_fandom: dict,
    fandom_images: dict,
    dry_run: bool,
    verbose: bool = True,
) -> str:
    """Generic handler for weapons/modules/reactors/shields/chassis."""
    entries   = extract_lua_entries(content)
    changes   = 0
    new_items = []

    for cache_key, cache_data in cache.items():
        if not isinstance(cache_data, dict):
            continue

        # Determine wiki title for this cache entry
        wiki_title = CACHE_TO_WIKI_TITLE.get(cache_key, cache_key)

        if wiki_title not in entries:
            if data_type == "chassis":
                # Don't auto-add chassis (uncertain which are playable)
                continue
            new_items.append((wiki_title, cache_key, cache_data))
            continue

        entry_text, start, end = entries[wiki_title]
        new_entry = entry_text

        # Update numeric / percent fields
        for section, wiki_field, cache_field, is_pct in field_map:
            if cache_field not in cache_data:
                continue
            cache_val = cache_data[cache_field]
            wiki_val  = get_section_value(new_entry, section, wiki_field)

            if values_equal(wiki_val, cache_val, is_pct):
                continue

            new_lua = fmt_lua(cache_val, is_percent=is_pct)
            updated = set_section_value(new_entry, section, wiki_field, new_lua)
            if updated != new_entry:
                if verbose:
                    old_disp = repr(wiki_val)
                    new_disp = repr(cache_val) + (' (pct)' if is_pct else '')
                    print(f"  [{data_type}] {wiki_title!r}: [{section}][{wiki_field}] "
                          f"{old_disp} â†’ {new_disp}")
                new_entry = updated
                changes  += 1

        # Update image1
        current_img = get_top_level_value(new_entry, 'image1')
        best_img    = resolve_image(wiki_title, item_to_fandom, fandom_images)
        if best_img and (current_img is None or current_img.lower() not in fandom_images):
            new_entry = set_top_level_value(new_entry, 'image1', f'"{best_img}"')
            if verbose:
                print(f"  [{data_type}] {wiki_title!r}: image1 {current_img!r} â†’ {best_img!r}")
            changes += 1

        if new_entry != entry_text:
            content = content[:start] + new_entry + content[end:]
            # Refresh entry positions after in-place edit (lengths may differ)
            entries = extract_lua_entries(content)

    # Add missing entries before the closing '}'
    if new_items:
        insert_before = content.rfind('\n}')
        if insert_before == -1:
            insert_before = len(content)
        additions = []
        for wiki_title, cache_key, cache_data in new_items:
            img  = resolve_image(wiki_title, item_to_fandom, fandom_images)
            text = gen_entry_fn(wiki_title, cache_data, img)
            additions.append(text)
            if verbose:
                print(f"  [{data_type}] ADD {wiki_title!r}")
        insert_str = '\n' + '\n'.join(additions) + '\n'
        content = content[:insert_before] + insert_str + content[insert_before:]
        changes += len(new_items)

    print(f"  [{data_type}] {changes} change(s) applied.")
    return content


def process_enemies(
    cache: dict,
    content: str,
    item_to_fandom: dict,
    fandom_images: dict,
    dry_run: bool,
) -> str:
    """Update or add enemy entries."""
    entries = extract_lua_entries(content)
    changes   = 0
    new_items = []

    for enemy_title, d in cache.items():
        if not isinstance(d, dict):
            continue

        if enemy_title not in entries:
            new_items.append((enemy_title, d))
            continue

        entry_text, start, end = entries[enemy_title]
        new_entry = entry_text

        # Update loadout
        updated = update_enemy_loadout(new_entry, d)
        if updated != new_entry:
            print(f"  [enemies] {enemy_title!r}: loadout updated")
            new_entry = updated
            changes  += 1

        # Update image1 using equipment_images.Chassis first, then catalog lookup
        current_img = get_top_level_value(new_entry, 'image1')
        best_img    = None
        chassis_imgs = d.get("equipment_images", {}).get("Chassis", [])
        if chassis_imgs:
            # The chassis image path is like "images/db/chassisdef/enemy_trike.png"
            src = chassis_imgs[0].split("/")[-1]
            best_img = fandom_images.get(src.lower())
        if not best_img:
            best_img = resolve_image(enemy_title, item_to_fandom, fandom_images)

        if best_img and (current_img is None or current_img.lower() not in fandom_images):
            new_entry = set_top_level_value(new_entry, 'image1', f'"{best_img}"')
            print(f"  [enemies] {enemy_title!r}: image1 {current_img!r} â†’ {best_img!r}")
            changes += 1

        if new_entry != entry_text:
            content = content[:start] + new_entry + content[end:]
            entries = extract_lua_entries(content)

    # Add entirely missing enemies
    if new_items:
        insert_before = content.rfind('\n}')
        if insert_before == -1:
            insert_before = len(content)
        additions = []
        for title, d in new_items:
            img   = None
            chassis_imgs = d.get("equipment_images", {}).get("Chassis", [])
            if chassis_imgs:
                src = chassis_imgs[0].split("/")[-1]
                img = fandom_images.get(src.lower())
            if not img:
                img = resolve_image(title, item_to_fandom, fandom_images)
            text  = gen_enemy_entry(title, d, img)
            additions.append(text)
            print(f"  [enemies] ADD {title!r}")
        insert_str = '\n' + '\n'.join(additions) + '\n'
        content = content[:insert_before] + insert_str + content[insert_before:]
        changes += len(new_items)

    print(f"  [enemies] {changes} change(s) applied.")
    return content


# â”€â”€â”€ Main â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true',
                        help='Print planned changes without writing files')
    parser.add_argument('--type', choices=list(WIKI_FILES.keys()),
                        help='Process only this data type')
    args = parser.parse_args()

    # Load shared image data
    catalog_path  = REFS / "knowledge" / "image_catalog.json"
    allimages_path = WORKSPACE / "cybots_wiki" / "allimages.json"
    catalog   = json.loads(catalog_path.read_text(encoding='utf-8'))
    allimages = json.loads(allimages_path.read_text(encoding='utf-8'))["query"]["allimages"]
    fandom_images, item_to_fandom = build_image_index(catalog, allimages)

    types_to_run = [args.type] if args.type else list(WIKI_FILES.keys())

    dispatch = {
        "weapons":  (WEAPONS_FIELDS,  gen_weapon_entry),
        "modules":  (MODULES_FIELDS,  gen_module_entry),
        "reactors": (REACTORS_FIELDS, gen_reactor_entry),
        "shields":  (SHIELDS_FIELDS,  gen_shield_entry),
        "chassis":  (CHASSIS_FIELDS,  None),  # no add for chassis
    }

    for dtype in types_to_run:
        wiki_path  = WIKI_FILES[dtype]
        cache_path = CACHE_FILES[dtype]

        if not cache_path.exists():
            print(f"[{dtype}] Cache file not found: {cache_path}")
            continue
        if not wiki_path.exists():
            print(f"[{dtype}] Wiki file not found: {wiki_path}")
            continue

        cache   = json.loads(cache_path.read_text(encoding='utf-8'))
        content = wiki_path.read_text(encoding='utf-8')

        print(f"\n=== Processing {dtype} ({wiki_path.name}) ===")

        if dtype == "enemies":
            new_content = process_enemies(
                cache, content, item_to_fandom, fandom_images, args.dry_run
            )
        else:
            field_map, gen_fn = dispatch[dtype]
            new_content = process_stats_file(
                dtype, cache, content, field_map, gen_fn,
                item_to_fandom, fandom_images, args.dry_run,
            )

        if new_content != content:
            if args.dry_run:
                print(f"  [{dtype}] DRY RUN â€” file not written.")
            else:
                wiki_path.write_text(new_content, encoding='utf-8')
                print(f"  [{dtype}] Written: {wiki_path}")
        else:
            print(f"  [{dtype}] No changes needed.")


if __name__ == "__main__":
    main()

