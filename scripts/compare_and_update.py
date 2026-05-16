#!/usr/bin/env python3
"""
Comprehensive comparison and update script for Cybots Wiki data modules.
Compares cache JSON files against wiki Lua data files and reports/applies differences.
"""

import json
import re
import os
import sys
from copy import deepcopy

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFS_DIR = os.path.join(BASE_DIR, 'REFERENCES')
WIKI_DIR = os.path.join(BASE_DIR, 'cybots_wiki', 'pages', 'Module')


# ─── JSON Cache Loading ───────────────────────────────────────────────────────

def load_json(filename):
    path = os.path.join(REFS_DIR, filename)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


# ─── Lua Wiki File Parsing ────────────────────────────────────────────────────

def extract_entries_from_lua(content):
    """Extract all title → (text, start, end) mappings from Lua table."""
    entries = {}
    title_pat = re.compile(r'title\s*=\s*"([^"]+)"')
    for m in title_pat.finditer(content):
        title = m.group(1)
        pos = m.start()
        # Find outer { ... } wrapping this entry
        entry_start = pos
        for i in range(pos - 1, -1, -1):
            if content[i] == '{':
                entry_start = i
                break
        # Walk forward to find matching close brace
        depth = 0
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


def get_lua_scalar(entry_text, field):
    """Extract a scalar value for a field in the entry text."""
    # Match: ["field"] = 123  or  ["field"] = 123.45  or  ["field"] = "str"  or  ["field"] = nil
    pat = re.compile(
        r'\["' + re.escape(field) + r'"\]\s*=\s*('
        r'nil'
        r'|"[^"]*"'
        r'|[-]?\d+(?:\.\d+)?'
        r'|\{[^}]+\}'  # inline table like { value = ..., unit = ... }
        r')',
        re.DOTALL
    )
    m = pat.search(entry_text)
    if not m:
        return None
    raw = m.group(1).strip()
    if raw == 'nil':
        return None
    if raw.startswith('"'):
        return raw.strip('"')
    if raw.startswith('{'):
        # parse { value = X, unit = "Y" }
        vm = re.search(r'value\s*=\s*([-]?\d+(?:\.\d+)?)', raw)
        if vm:
            v = vm.group(1)
            return float(v) if '.' in v else int(v)
        return raw
    v = raw
    return float(v) if '.' in v else int(v)


def get_lua_section_value(entry_text, section, field):
    """Extract a scalar value from within a named section."""
    sec_pat = re.compile(r'\["' + re.escape(section) + r'"\]\s*=\s*\{', re.DOTALL)
    sm = sec_pat.search(entry_text)
    if not sm:
        return None
    # Find the section's closing brace
    start = sm.end() - 1
    depth = 0
    sec_end = start
    for i in range(start, len(entry_text)):
        if entry_text[i] == '{':
            depth += 1
        elif entry_text[i] == '}':
            depth -= 1
            if depth == 0:
                sec_end = i + 1
                break
    section_text = entry_text[start:sec_end]
    return get_lua_scalar(section_text, field)


# ─── Value Comparison ─────────────────────────────────────────────────────────

def values_match(wiki_val, cache_val):
    """Return True if values are effectively equal."""
    if wiki_val is None and cache_val is None:
        return True
    if wiki_val is None or cache_val is None:
        return False
    try:
        return abs(float(wiki_val) - float(cache_val)) < 0.0001
    except (TypeError, ValueError):
        return str(wiki_val).strip().lower() == str(cache_val).strip().lower()


# ─── Lua Entry Rewriting ──────────────────────────────────────────────────────

def set_lua_field_in_section(entry_text, section, field, new_value):
    """
    Replace the value of `field` inside `section` in `entry_text`.
    Handles both simple and { value=..., unit=... } forms.
    Returns updated entry_text.
    """
    # Find section boundaries
    sec_pat = re.compile(r'(\["' + re.escape(section) + r'"\]\s*=\s*\{)', re.DOTALL)
    sm = sec_pat.search(entry_text)
    if not sm:
        return entry_text

    sec_open_end = sm.end()
    start = sec_open_end - 1
    depth = 0
    sec_end = start
    for i in range(start, len(entry_text)):
        if entry_text[i] == '{':
            depth += 1
        elif entry_text[i] == '}':
            depth -= 1
            if depth == 0:
                sec_end = i + 1
                break

    section_text = entry_text[start:sec_end]
    new_section = _replace_value_in_text(section_text, field, new_value)
    return entry_text[:start] + new_section + entry_text[sec_end:]


def _replace_value_in_text(text, field, new_value):
    """Replace field value in a block of Lua text."""
    fmtval = _fmt_lua_value(new_value)

    # Try { value = X, unit = "Y" } form first
    complex_pat = re.compile(
        r'(\["' + re.escape(field) + r'"\]\s*=\s*\{\s*value\s*=\s*)([-]?\d+(?:\.\d+)?)',
        re.DOTALL
    )
    m = complex_pat.search(text)
    if m:
        return text[:m.start(2)] + str(new_value) + text[m.end(2):]

    # Simple form: ["field"] = 123  or nil  or "str"
    simple_pat = re.compile(
        r'(\["' + re.escape(field) + r'"\]\s*=\s*)(nil|"[^"]*"|[-]?\d+(?:\.\d+)?)',
        re.DOTALL
    )
    m = simple_pat.search(text)
    if m:
        return text[:m.start(2)] + fmtval + text[m.end(2):]

    return text


def _fmt_lua_value(value):
    if value is None:
        return 'nil'
    if isinstance(value, str):
        return f'"{value}"'
    if isinstance(value, float):
        if value == int(value):
            return str(int(value))
        return str(value)
    return str(value)


# ─── Percentage field handling ────────────────────────────────────────────────

def cache_to_pct(v):
    """Convert 0-1 fraction to percentage integer (e.g. 0.01 → 1, 0.2 → 20)."""
    if v is None:
        return None
    return round(v * 100)


# ─── Comparison Helpers ───────────────────────────────────────────────────────

class Diff:
    def __init__(self, title, section, field, wiki_val, cache_val):
        self.title = title
        self.section = section
        self.field = field
        self.wiki_val = wiki_val
        self.cache_val = cache_val

    def __str__(self):
        return f"  [{self.title}] {self.section}/{self.field}: wiki={self.wiki_val!r} → cache={self.cache_val!r}"


# ─── WEAPONS ─────────────────────────────────────────────────────────────────

WEAPON_FIELD_MAP = {
    # cache_key: (section, wiki_field, transform)
    'shield_damage':   ('Properties', 'Shield Damage', None),
    'armor_damage':    ('Properties', 'Armor Piercing', None),
    'energy_drain':    ('Properties', 'Energy Drain', None),
    'damage_radius':   ('Properties', 'Damage Radius', None),
    'accuracy':        ('Properties', 'Accuracy', None),
    'shots_per_turn':  ('Properties', 'Shots Per Turn', None),
    'energy_per_shot': ('Properties', 'Energy Per Shot', None),
    'merit':           ('Properties', 'Offensive Merit', None),
}

WEAPON_NAME_MAP = {
    'Shield Disrupter': 'Shield Disruptor',
    'Adv. Cyclic Laser': 'Advanced Cyclic Laser',
}


def compare_weapons(cache, wiki_entries):
    diffs = []
    missing = []
    for name, cdata in cache.items():
        wiki_name = WEAPON_NAME_MAP.get(name, name)
        if wiki_name not in wiki_entries:
            missing.append(name)
            continue
        entry_text, _, _ = wiki_entries[wiki_name]
        for ckey, (section, wfield, xform) in WEAPON_FIELD_MAP.items():
            if ckey not in cdata:
                continue
            cval = cdata[ckey]
            if xform:
                cval = xform(cval)
            wval = get_lua_section_value(entry_text, section, wfield)
            if not values_match(wval, cval):
                diffs.append(Diff(wiki_name, section, wfield, wval, cval))
    return diffs, missing


# ─── MODULES ─────────────────────────────────────────────────────────────────

MODULE_FIELD_MAP = {
    'merit':                 ('Properties', 'Defensive Merit', None),
    'energy_use':            ('Properties', 'Energy Use', None),
    'critical_hit_chance':   ('Properties', 'Critical Hit Chance', cache_to_pct),
    'speed':                 ('Properties', 'Speed', cache_to_pct),
    'accuracy_boost':        ('Properties', 'Accuracy', cache_to_pct),
    'firing_rate':           ('Properties', 'Firing Rate', cache_to_pct),
    'shield_deflection':     ('Properties', 'Shield Deflection', cache_to_pct),
    'armor_deflection':      ('Properties', 'Armor Deflection', cache_to_pct),
    'energy_drain_deflection':('Properties', 'Energy Drain Deflection', cache_to_pct),
}

# Cache internal names → wiki display names
MODULE_NAME_MAP = {
    'Plutonium Core Module': 'Plutonium Core',
    'Hyper Drive Module': 'Hyper Drive',
}

# Cache entries to skip entirely (admin/cheat modules)
MODULE_SKIP = {'prometeus module'}

# Display title to use when adding to wiki (overrides cache key casing)
MODULE_TITLE_OVERRIDES = {
    'basewall Effect': 'Basewall Effect',
}


def compare_modules(cache, wiki_entries):
    diffs = []
    missing = []
    for name, cdata in cache.items():
        if name in MODULE_SKIP:
            continue
        wiki_name = MODULE_NAME_MAP.get(name, name)
        if wiki_name not in wiki_entries:
            missing.append(name)
            continue
        entry_text, _, _ = wiki_entries[wiki_name]
        for ckey, (section, wfield, xform) in MODULE_FIELD_MAP.items():
            if ckey not in cdata:
                continue
            cval = cdata[ckey]
            if xform:
                cval = xform(cval)
            wval = get_lua_section_value(entry_text, section, wfield)
            if not values_match(wval, cval):
                diffs.append(Diff(wiki_name, section, wfield, wval, cval))
    return diffs, missing


# ─── REACTORS ────────────────────────────────────────────────────────────────

REACTOR_FIELD_MAP = {
    'max_power':    ('Properties', 'Max Energy Level', None),
    'recharge_rate':('Properties', 'Recharge Rate', None),
    'merit':        ('Properties', 'Defensive Merit', None),
}

REACTOR_NAME_MAP = {
    'Magtronic Powercell': 'Magtronic Power Cell',
}


def compare_reactors(cache, wiki_entries):
    diffs = []
    missing = []
    for name, cdata in cache.items():
        wiki_name = REACTOR_NAME_MAP.get(name, name)
        if wiki_name not in wiki_entries:
            missing.append(name)
            continue
        entry_text, _, _ = wiki_entries[wiki_name]
        for ckey, (section, wfield, xform) in REACTOR_FIELD_MAP.items():
            if ckey not in cdata:
                continue
            cval = cdata[ckey]
            if xform:
                cval = xform(cval)
            wval = get_lua_section_value(entry_text, section, wfield)
            if not values_match(wval, cval):
                diffs.append(Diff(wiki_name, section, wfield, wval, cval))
    return diffs, missing


# ─── SHIELDS ─────────────────────────────────────────────────────────────────

SHIELD_FIELD_MAP = {
    'primary_level': ('Properties', 'Primary Level', None),
    'energy_use':    ('Properties', 'Energy Use', None),
    'recharge_rate': ('Properties', 'Recharge Rate', None),
    'merit':         ('Properties', 'Defensive Merit', None),
}

# Cache shield names → wiki display names (for shields_data comparison)
SHIELD_NAME_MAP = {
    'Baron': 'Baron (Shield)',
    'Argon': 'Argon (Shield)',
    'Plasma': 'Plasma (Shield)',
    'SXD10': 'SxD10',
}


def compare_shields(cache, wiki_entries):
    diffs = []
    missing = []
    for name, cdata in cache.items():
        wiki_name = SHIELD_NAME_MAP.get(name, name)
        if wiki_name not in wiki_entries:
            missing.append(name)
            continue
        entry_text, _, _ = wiki_entries[wiki_name]
        for ckey, (section, wfield, xform) in SHIELD_FIELD_MAP.items():
            if ckey not in cdata:
                continue
            cval = cdata[ckey]
            if xform:
                cval = xform(cval)
            wval = get_lua_section_value(entry_text, section, wfield)
            if not values_match(wval, cval):
                diffs.append(Diff(wiki_name, section, wfield, wval, cval))
    return diffs, missing


# ─── CHASSIS ─────────────────────────────────────────────────────────────────

CHASSIS_FIELD_MAP = {
    'armor':           ('Base Stats', 'Armor', None),
    'speed':           ('Base Stats', 'Speed', None),
    'critical_hit_chance': ('Base Stats', 'Critical Hit Chance', cache_to_pct),
    'shield_projection':   ('Unique Stats', 'Shield Projection', cache_to_pct),
    'module_uplink':       ('Unique Stats', 'Module Uplink', cache_to_pct),
    'energy_share':        ('Unique Stats', 'Energy Distribution / Energy Share', cache_to_pct),
    'damage_boost':        ('Hidden Stats', 'Damage Boost', cache_to_pct),
    'drain_boost':         ('Hidden Stats', 'Drain Boost', cache_to_pct),
    'weapon_slots':        ('Slots', 'Weapon Slots', None),
    'shield_slots':        ('Slots', 'Shield Slots', None),
    'module_slots':        ('Slots', 'Module Slots', None),
    'payload':             ('Base Stats', 'Payload', None),
}

# CyCorps variants have different wiki titles
CHASSIS_NAME_MAP = {
    'CyCorps Ranger':    'CyCorps Ranger',
    'CyCorps Overseer':  'CyCorps Overseer',
    'CyCorps Marauder':  'CyCorps Marauder',
    'CyCorps Orbiter':   'CyCorps Orbiter',
    'CyCorps Leviathan': 'CyCorps Leviathan',
    'CyCorps Sentinel':  'CySentinel',
}


def compare_chassis(cache, wiki_entries):
    diffs = []
    missing = []
    for name, cdata in cache.items():
        wiki_name = CHASSIS_NAME_MAP.get(name, name)
        if wiki_name not in wiki_entries:
            missing.append(f"{name} (as {wiki_name})")
            continue
        entry_text, _, _ = wiki_entries[wiki_name]
        for ckey, (section, wfield, xform) in CHASSIS_FIELD_MAP.items():
            if ckey not in cdata:
                continue
            cval = cdata[ckey]
            if xform:
                cval = xform(cval)
            wval = get_lua_section_value(entry_text, section, wfield)
            if not values_match(wval, cval):
                diffs.append(Diff(wiki_name, section, wfield, wval, cval))
    return diffs, missing


# ─── ENEMIES ─────────────────────────────────────────────────────────────────

# Cache names with typos/variants → wiki names
ENEMY_NAME_MAP = {
    'Scaen Grenadiers': 'Scaven Grenadiers',
}

# For enemy entries, shield display name → wiki URL slug (disambiguation)
ENEMY_SHIELD_URL_MAP = {
    'Baron': 'Baron_(Shield)',
    'Argon': 'Argon_(Shield)',
    'Plasma': 'Plasma_(Shield)',
}


def compare_enemies(cache, wiki_entries):
    diffs = []
    missing = []

    for name, cdata in cache.items():
        wiki_name = ENEMY_NAME_MAP.get(name, name)
        if wiki_name not in wiki_entries:
            missing.append(name)
            continue
        entry_text, _, _ = wiki_entries[wiki_name]

        # Check chassis
        cache_chassis = cdata.get('chassis')
        wiki_chassis_name = get_lua_scalar(entry_text, 'name') if 'chassis' in entry_text else None
        # More precise: find chassis block
        cm = re.search(r'chassis\s*=\s*\{[^}]*name\s*=\s*"([^"]*)"', entry_text)
        wiki_chassis = cm.group(1) if cm else None
        if cache_chassis and wiki_chassis and wiki_chassis != cache_chassis:
            diffs.append(Diff(name, 'chassis', 'name', wiki_chassis, cache_chassis))

        # Check reactor
        cache_reactor = cdata.get('reactor')
        rm = re.search(r'reactor\s*=\s*\{[^}]*name\s*=\s*"([^"]*)"', entry_text)
        wiki_reactor = rm.group(1) if rm else (None if re.search(r'reactor\s*=\s*nil', entry_text) else 'MISSING')
        if cache_reactor is None:
            # should be nil in wiki
            if rm is not None:
                diffs.append(Diff(name, 'reactor', 'name', wiki_reactor, None))
        elif wiki_reactor != cache_reactor:
            diffs.append(Diff(name, 'reactor', 'name', wiki_reactor, cache_reactor))

        # Check weapons list
        cache_weapons = cdata.get('weapons', [])
        wiki_weapons_matches = re.findall(r'\{\s*name\s*=\s*"([^"]+)"[^}]*\}', 
                                           _extract_list_block(entry_text, 'weapons'))
        if sorted(cache_weapons) != sorted(wiki_weapons_matches):
            if cache_weapons != wiki_weapons_matches:  # order matters too but log anyway
                diffs.append(Diff(wiki_name, 'weapons', 'list',
                                   wiki_weapons_matches, cache_weapons))

        # Check shields list
        cache_shields = cdata.get('shields', [])
        wiki_shields_matches = re.findall(r'\{\s*name\s*=\s*"([^"]+)"[^}]*\}',
                                           _extract_list_block(entry_text, 'shields'))
        if sorted(cache_shields) != sorted(wiki_shields_matches):
            if cache_shields != wiki_shields_matches:
                diffs.append(Diff(wiki_name, 'shields', 'list',
                                   wiki_shields_matches, cache_shields))

        # Check modules list
        cache_modules = cdata.get('modules', [])
        wiki_modules_matches = re.findall(r'\{\s*name\s*=\s*"([^"]+)"[^}]*\}',
                                           _extract_list_block(entry_text, 'modules'))
        if sorted(cache_modules) != sorted(wiki_modules_matches):
            if cache_modules != wiki_modules_matches:
                diffs.append(Diff(wiki_name, 'modules', 'list',
                                   wiki_modules_matches, cache_modules))

    return diffs, missing


def _extract_list_block(entry_text, field):
    """Extract the { ... } block for weapons/shields/modules list."""
    pat = re.compile(r'\b' + re.escape(field) + r'\s*=\s*\{', re.DOTALL)
    m = pat.search(entry_text)
    if not m:
        return ''
    start = m.end() - 1
    depth = 0
    end = start
    for i in range(start, len(entry_text)):
        if entry_text[i] == '{':
            depth += 1
        elif entry_text[i] == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    return entry_text[start:end]


# ─── Apply diffs ──────────────────────────────────────────────────────────────

def apply_diffs(content, wiki_entries, diffs):
    """Apply all diffs to content, return updated content."""
    # Sort diffs in reverse order by position to avoid offset issues
    # We'll apply by rebuilding entries

    # Group diffs by title
    by_title = {}
    for d in diffs:
        if d.title not in by_title:
            by_title[d.title] = []
        by_title[d.title].append(d)

    for title, title_diffs in by_title.items():
        if title not in wiki_entries:
            continue
        entry_text, start, end = wiki_entries[title]
        new_entry = entry_text

        for d in title_diffs:
            if d.section in ('weapons', 'shields', 'modules', 'chassis', 'reactor'):
                # Enemy list/equipment diffs need special handling - skip for now
                # (handled separately)
                continue
            new_entry = set_lua_field_in_section(new_entry, d.section, d.field, d.cache_val)

        if new_entry != entry_text:
            content = content[:start] + new_entry + content[end:]
            # Recalculate positions for subsequent entries
            # Since we're replacing same-length isn't guaranteed, re-parse
            wiki_entries = extract_entries_from_lua(content)

    return content


# ─── New entry generation ─────────────────────────────────────────────────────

def make_reactor_entry(name, data):
    """Generate a Lua entry for a new reactor."""
    slug = name.lower().replace(' ', '').replace('-', '').replace('.', '').replace('(', '').replace(')', '')
    image = f"{slug}.jpg"
    url = f"https://cybots.fandom.com/wiki/{name.replace(' ', '_')}"
    return f'''    {{
        title = "{name}",
        url = "{url}",
        image1 = "{image}",
        sections = {{
            ["Unit Information"] = {{
                ["Cost"] = nil,
                ["Weight"] = nil,
                ["Required Tech Level"] = nil,
                ["Other Requirements"] = "none",
            }},
            ["Properties"] = {{
                ["Max Energy Level"] = {data.get('max_power', 'nil')},
                ["Recharge Rate"] = {data.get('recharge_rate', 'nil')},
                ["Defensive Merit"] = {data.get('merit', 'nil')},
            }},
        }},
    }},'''


def make_shield_entry(name, data):
    """Generate a Lua entry for a new shield."""
    slug = name.lower().replace(' ', '').replace('-', '').replace('.', '').replace('(', '').replace(')', '').replace('_', '')
    image = f"{slug}.jpg"
    url = f"https://cybots.fandom.com/wiki/{name.replace(' ', '_')}"
    return f'''    {{
        title = "{name}",
        url = "{url}",
        image1 = "{image}",
        sections = {{
            ["Unit Information"] = {{
                ["Cost"] = nil,
                ["Weight"] = nil,
                ["Required Tech Level"] = nil,
                ["Other Requirements"] = "none",
            }},
            ["Properties"] = {{
                ["Primary Level"] = {data.get('primary_level', 'nil')},
                ["Energy Use"] = {data.get('energy_use', 'nil')},
                ["Recharge Rate"] = {data.get('recharge_rate', 'nil')},
                ["Defensive Merit"] = {data.get('merit', 'nil')},
            }},
        }},
    }},'''


def make_weapon_entry(name, data):
    """Generate a Lua entry for a new weapon."""
    slug = name.lower().replace(' ', '').replace('-', '').replace('.', '').replace('(', '').replace(')', '')
    image = f"{slug}.jpg"
    url = f"https://cybots.fandom.com/wiki/{name.replace(' ', '_')}"
    sd = data.get('shield_damage', 'nil')
    ap = data.get('armor_damage', 'nil')
    ed = data.get('energy_drain', 'nil') if 'energy_drain' in data else 0
    dr = data.get('damage_radius', 1)
    acc = data.get('accuracy', 'nil')
    spt = data.get('shots_per_turn', 'nil')
    eps = data.get('energy_per_shot', 'nil')
    merit = data.get('merit', 'nil')
    return f'''    {{
        title = "{name}",
        url = "{url}",
        image1 = "{image}",
        sections = {{
            ["Unit Information"] = {{
                ["Cost"] = nil,
                ["Weapon Type"] = nil,
                ["Other Requirements"] = "none",
            }},
            ["Properties"] = {{
                ["Weight"] = nil,
                ["Required Tech Level"] = nil,
                ["Shield Damage"] = {sd if sd != 'nil' else 'nil'},
                ["Armor Piercing"] = {ap if ap != 'nil' else 'nil'},
                ["Energy Drain"] = {ed},
                ["Damage Radius"] = {dr},
                ["Accuracy"] = {acc},
                ["Shots Per Turn"] = {spt},
                ["Energy Per Shot"] = {eps},
                ["Max Targets Per Turn"] = nil,
                ["Offensive Merit"] = {merit},
            }},
        }},
    }},'''


def make_module_entry(name, data):
    """Generate a Lua entry for a new module."""
    # Apply any title overrides (e.g. capitalize 'basewall Effect')
    display_name = MODULE_TITLE_OVERRIDES.get(name, name)
    slug = display_name.lower().replace(' ', '').replace('-', '').replace('.', '').replace('(', '').replace(')', '')
    image = f"Module1.jpg"
    url = f"https://cybots.fandom.com/wiki/{display_name.replace(' ', '_')}"
    name = display_name  # use display name in the entry
    merit = data.get('merit', 0)
    eu = data.get('energy_use', 'nil')
    chc = f"{{ value = {cache_to_pct(data['critical_hit_chance'])}, unit = \"%\" }}" if 'critical_hit_chance' in data else 'nil'
    spd = f"{{ value = {cache_to_pct(data['speed'])}, unit = \"%\" }}" if 'speed' in data else 'nil'
    acc = f"{{ value = {cache_to_pct(data['accuracy_boost'])}, unit = \"%\" }}" if 'accuracy_boost' in data else 'nil'
    fr = f"{{ value = {cache_to_pct(data['firing_rate'])}, unit = \"%\" }}" if 'firing_rate' in data else 'nil'
    sd = f"{{ value = {cache_to_pct(data['shield_deflection'])}, unit = \"%\" }}" if 'shield_deflection' in data else 'nil'
    ad = f"{{ value = {cache_to_pct(data['armor_deflection'])}, unit = \"%\" }}" if 'armor_deflection' in data else 'nil'
    edd = f"{{ value = {cache_to_pct(data['energy_drain_deflection'])}, unit = \"%\" }}" if 'energy_drain_deflection' in data else 'nil'
    return f'''    {{
        title = "{name}",
        url = "{url}",
        image1 = "{image}",
        sections = {{
            ["Unit Information"] = {{
                ["Cost"] = nil,
                ["Module Type"] = nil,
                ["Other Requirements"] = "none",
            }},
            ["Properties"] = {{
                ["Weight"] = nil,
                ["Required Tech Level"] = nil,
                ["Energy Use"] = {eu},
                ["Speed"] = {spd},
                ["Critical Hit Chance"] = {chc},
                ["Accuracy"] = {acc},
                ["Firing Rate"] = {fr},
                ["Shield Deflection"] = {sd},
                ["Armor Deflection"] = {ad},
                ["Energy Efficiency"] = nil,
                ["Energy Drain Deflection"] = {edd},
                ["Bounty Enhanced"] = nil,
                ["Experience Enhanced"] = nil,
                ["Defensive Merit"] = {merit},
            }},
        }},
    }},'''


def make_enemy_entry(name, data):
    """Generate a Lua entry for a new enemy."""
    def chassis_block(n):
        if not n:
            return 'nil'
        slug = n.replace(' ', '_')
        return f'{{ name = "{n}", url = url("{slug}") }}'

    def item_block(item_name, is_shield=False):
        slug = item_name.replace(' ', '_')
        if is_shield:
            slug = ENEMY_SHIELD_URL_MAP.get(item_name, slug)
        return f'{{ name = "{item_name}", url = url("{slug}") }}'

    def item_list(items, is_shield=False):
        if not items:
            return '{}'
        lines = []
        for item in items:
            lines.append(f'            {item_block(item, is_shield)},')
        return '{\n' + '\n'.join(lines) + '\n        }'

    chassis = data.get('chassis')
    reactor = data.get('reactor')
    shields = data.get('shields', [])
    weapons = data.get('weapons', [])
    modules = data.get('modules', [])

    name_slug = name.replace(' ', '_')
    reactor_str = chassis_block(reactor) if reactor else 'nil'
    chassis_str = chassis_block(chassis) if chassis else 'nil'

    return f'''    {{
        title = "{name}",
        url = url("{name_slug}"),
        chassis = {chassis_str},
        reactor = {reactor_str},
        shields = {item_list(shields, is_shield=True)},
        weapons = {item_list(weapons)},
        modules = {item_list(modules)},
    }},'''


# ─── Main ─────────────────────────────────────────────────────────────────────

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def write_file(path, content):
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)


def process_file(data_name, cache, compare_fn, make_entry_fn, apply_mode=True):
    filepath = os.path.join(WIKI_DIR, f'{data_name}.wikitext')
    content = read_file(filepath)
    wiki_entries = extract_entries_from_lua(content)

    diffs, missing = compare_fn(cache, wiki_entries)

    print(f"\n{'='*60}")
    print(f"  {data_name}")
    print(f"{'='*60}")

    if diffs:
        print(f"\nValue diffs ({len(diffs)}):")
        for d in diffs:
            print(str(d))
    else:
        print("\nNo value diffs found.")

    if missing:
        print(f"\nMissing entries ({len(missing)}):")
        for m in missing:
            print(f"  - {m}")
    else:
        print("No missing entries.")

    if apply_mode and diffs:
        print("\nApplying diffs...")
        new_content = apply_diffs(content, wiki_entries, diffs)
        # Re-parse after diffs applied
        write_file(filepath, new_content)
        print(f"  Written {filepath}")

    if apply_mode and missing and make_entry_fn:
        print("\nAdding missing entries...")
        content_for_append = read_file(filepath)
        # Find insert point: before last `}` of the return table
        insert_pos = content_for_append.rfind('\n}')
        if insert_pos == -1:
            print("  ERROR: Could not find insert position.")
            return

        new_entries = []
        for m in missing:
            cache_name = m.split(' (as ')[0]  # strip alias note
            if cache_name in cache:
                entry_text = make_entry_fn(cache_name, cache[cache_name])
                new_entries.append(entry_text)

        if new_entries:
            additions = '\n' + '\n'.join(new_entries) + '\n'
            new_content = content_for_append[:insert_pos] + additions + content_for_append[insert_pos:]
            write_file(filepath, new_content)
            print(f"  Added {len(new_entries)} new entries to {filepath}")


def main():
    print("Loading cache files...")
    weapons_cache = load_json('weapons_cache.json')
    modules_cache = load_json('modules_cache.json')
    reactors_cache = load_json('reactors_cache.json')
    shields_cache = load_json('shields_cache.json')
    chassis_cache = load_json('chassis_cache.json')
    enemies_cache = load_json('enemies_cache.json')

    apply = '--apply' in sys.argv or len(sys.argv) == 1

    process_file('Weapons_data', weapons_cache, compare_weapons, make_weapon_entry, apply)
    process_file('Modules_data', modules_cache, compare_modules, make_module_entry, apply)
    process_file('Reactors_data', reactors_cache, compare_reactors, make_reactor_entry, apply)
    process_file('Shields_data', shields_cache, compare_shields, make_shield_entry, apply)
    process_file('Chassis_data', chassis_cache, compare_chassis, None, apply)  # chassis missing entries handled manually
    process_file('Enemies_data', enemies_cache, compare_enemies, make_enemy_entry, apply)

    print("\nDone.")


if __name__ == '__main__':
    main()
