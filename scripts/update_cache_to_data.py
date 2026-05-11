#!/usr/bin/env python3
"""
Update Cybots Wiki data files based on cache values - improved version
"""
import json
import re

def find_entry_by_title(content, title):
    """Find and return a complete entry by title"""
    # Find the title line
    pattern = rf'title\s*=\s*"{re.escape(title)}"'
    match = re.search(pattern, content)
    if not match:
        return None, None
    
    # Work backwards to find the opening brace
    start = match.start()
    brace_count = 0
    entry_start = start
    for i in range(start - 1, -1, -1):
        if content[i] == '}':
            brace_count += 1
        elif content[i] == '{':
            if brace_count == 0:
                entry_start = i
                break
            brace_count -= 1
    
    # Work forwards to find the closing brace
    start = match.start()
    brace_count = 0
    found_opening = False
    entry_end = start
    for i in range(entry_start, len(content)):
        if content[i] == '{':
            brace_count += 1
            found_opening = True
        elif content[i] == '}' and found_opening:
            brace_count -= 1
            if brace_count == 0:
                entry_end = i + 1
                break
    
    return content[entry_start:entry_end], (entry_start, entry_end)

def update_value_in_section(entry_text, section_name, key, new_value):
    """Update a value within a section of an entry"""
    # Format the new value
    if isinstance(new_value, float) and 0 < new_value < 1:
        new_val_str = str(new_value)
    else:
        new_val_str = str(new_value)
    
    # Find the section
    section_pattern = rf'\["{section_name}"\]\s*=\s*\{{\s*'
    section_match = re.search(section_pattern, entry_text)
    if not section_match:
        return entry_text, False
    
    # Find the key-value pair in the section
    # Two patterns: simple values and complex { value = ..., unit = ... } values
    
    # Pattern 1: Simple numeric value like ["Key"] = 123
    simple_pattern = rf'(\["{re.escape(key)}"\]\s*=\s*)(\d+(?:\.\d+)?)'
    simple_match = re.search(simple_pattern, entry_text)
    
    if simple_match:
        old_text = simple_match.group(0)
        new_text = f'["{key}"] = {new_val_str}'
        new_entry = entry_text.replace(old_text, new_text)
        return new_entry, True
    
    # Pattern 2: Complex value like ["Key"] = { value = 123, unit = "%" }
    complex_pattern = rf'(\["{re.escape(key)}"\]\s*=\s*\{{\s*value\s*=\s*)(\d+(?:\.\d+)?)'
    complex_match = re.search(complex_pattern, entry_text)
    
    if complex_match:
        old_text = complex_match.group(0)
        new_text = f'["{key}"] = {{ value = {new_val_str}'
        new_entry = entry_text.replace(old_text, new_text)
        return new_entry, True
    
    return entry_text, False

def update_file(filepath, updates_list):
    """Apply all updates to a file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    for item_name, section, key, new_value in updates_list:
        entry_text, positions = find_entry_by_title(content, item_name)
        
        if entry_text is None:
            print(f"  ERROR: Could not find entry: {item_name}")
            continue
        
        new_entry, changed = update_value_in_section(entry_text, section, key, new_value)
        
        if changed:
            start, end = positions
            content = content[:start] + new_entry + content[end:]
            print(f"  ✓ Updated {item_name}: {section}.{key} = {new_value}")
        else:
            print(f"  ✗ Could not find field: {item_name}/{section}/{key}")
    
    return content

# Load cache files
with open('chassis_cache.json') as f:
    chassis_cache = json.load(f)
with open('weapons_cache.json') as f:
    weapons_cache = json.load(f)
with open('modules_cache.json') as f:
    modules_cache = json.load(f)
with open('reactors_cache.json') as f:
    reactors_cache = json.load(f)
with open('shields_cache.json') as f:
    shields_cache = json.load(f)

# Build update lists
chassis_updates = []
for item_name in ['Ranger', 'Orbiter', 'Valadin', 'Overseer', 'Sentinel', 'Marauder', 'Reaper', 'Bulwark', 'Crusader', 'Enhanced Reaper', 'Flaming Hornet', 'Flaming Orbiter', 'Hornet', 'Leviathan', 'Recon Hornet', 'Recon Warthog', 'Terminus Prototype', 'Viper', 'Warthog', 'CyCorps Overseer']:
    if item_name in chassis_cache:
        cache_entry = chassis_cache[item_name]
        
        if 'armor' in cache_entry:
            chassis_updates.append((item_name, 'Base Stats', 'Armor', cache_entry['armor']))
        if 'speed' in cache_entry:
            chassis_updates.append((item_name, 'Base Stats', 'Speed', cache_entry['speed']))
        if 'critical_hit_chance' in cache_entry:
            chassis_updates.append((item_name, 'Base Stats', 'Critical Hit Chance', cache_entry['critical_hit_chance']))

# File updates
print("Updating Chassis_data.wikitext...")
chassis_content = update_file('cybots_wiki/pages/Module/Chassis_data.wikitext', chassis_updates)
with open('cybots_wiki/pages/Module/Chassis_data.wikitext', 'w', encoding='utf-8') as f:
    f.write(chassis_content)

print("\nUpdating Weapons_data.wikitext...")
weapons_updates = [
    ('Good Samaritan', 'Properties', 'Shield Damage', weapons_cache['Good Samaritan']['shield_damage']),
]
weapons_content = update_file('cybots_wiki/pages/Module/Weapons_data.wikitext', weapons_updates)
with open('cybots_wiki/pages/Module/Weapons_data.wikitext', 'w', encoding='utf-8') as f:
    f.write(weapons_content)

print("\nUpdating Modules_data.wikitext...")
modules_updates = [
    ('Anomaly Detector', 'Properties', 'Defensive Merit', modules_cache['Anomaly Detector']['merit']),
    ('Security Countermand', 'Properties', 'Defensive Merit', modules_cache['Security Countermand']['merit']),
    ('ComWave Scanner', 'Properties', 'Defensive Merit', modules_cache['ComWave Scanner']['merit']),
]
modules_content = update_file('cybots_wiki/pages/Module/Modules_data.wikitext', modules_updates)
with open('cybots_wiki/pages/Module/Modules_data.wikitext', 'w', encoding='utf-8') as f:
    f.write(modules_content)

print("\nUpdating Reactors_data.wikitext...")
reactors_updates = [
    ('True Guard Cell', 'Properties', 'Max Energy Level', reactors_cache['True Guard Cell']['max_power']),
    ('True Guard Cell', 'Properties', 'Recharge Rate', reactors_cache['True Guard Cell']['recharge_rate']),
    ('True Guard Cell', 'Properties', 'Defensive Merit', reactors_cache['True Guard Cell']['merit']),
]
reactors_content = update_file('cybots_wiki/pages/Module/Reactors_data.wikitext', reactors_updates)
with open('cybots_wiki/pages/Module/Reactors_data.wikitext', 'w', encoding='utf-8') as f:
    f.write(reactors_content)

print("\nUpdating Shields_data.wikitext...")
shields_updates = [
    ('Photonic SV', 'Properties', 'Recharge Rate', shields_cache['Photonic SV']['recharge_rate']),
    ('Photonic DV', 'Properties', 'Recharge Rate', shields_cache['Photonic DV']['recharge_rate']),
    ('Photonic Sphere', 'Properties', 'Energy Use', shields_cache['Photonic Sphere']['energy_use']),
    ('Argon Array', 'Properties', 'Recharge Rate', shields_cache['Argon Array']['recharge_rate']),
]
shields_content = update_file('cybots_wiki/pages/Module/Shields_data.wikitext', shields_updates)
with open('cybots_wiki/pages/Module/Shields_data.wikitext', 'w', encoding='utf-8') as f:
    f.write(shields_content)

print("\nAll updates completed!")
