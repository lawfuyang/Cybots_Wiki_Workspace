import json
import re
import os

def update_lua_value(lua_text, item_title, section, key, new_value):
    """Update a value in the Lua text"""
    # Find the entry for this item
    entry_pattern = rf'title\s*=\s*"{re.escape(item_title)}"'
    entry_match = re.search(entry_pattern, lua_text)
    
    if not entry_match:
        return lua_text
    
    # Find the start and end of this entry
    start = entry_match.start()
    brace_depth = 0
    found_open = False
    entry_start = start
    
    for i in range(start, len(lua_text)):
        if lua_text[i] == '{':
            if not found_open:
                entry_start = i
            brace_depth += 1
            found_open = True
        elif lua_text[i] == '}' and found_open:
            brace_depth -= 1
            if brace_depth == 0:
                entry_end = i + 1
                break
    else:
        return lua_text
    
    entry_text = lua_text[entry_start:entry_end]
    
    # Find the section in the entry
    section_pattern = rf'\["{re.escape(section)}"\]\s*=\s*\{{([^}}]+)\}}'
    section_match = re.search(section_pattern, entry_text, re.DOTALL)
    
    if not section_match:
        return lua_text
    
    # Update the value in the section
    section_content = section_match.group(1)
    old_section = section_match.group(0)
    
    # Format the new value
    if new_value is None:
        new_val_str = 'nil'
    elif isinstance(new_value, str):
        new_val_str = f'"{new_value}"'
    elif isinstance(new_value, (int, float)):
        new_val_str = str(new_value)
    else:
        new_val_str = str(new_value)
    
    # Create the replacement pattern for the key-value pair
    old_pattern = rf'\["{re.escape(key)}"\]\s*=\s*[^,}}\n]+'
    new_section = re.sub(old_pattern, f'["{key}"] = {new_val_str}', old_section)
    
    # Replace in entry text
    new_entry = entry_text.replace(old_section, new_section)
    
    # Replace in full text
    return lua_text[:entry_start] + new_entry + lua_text[entry_end:]

# Mapping of updates needed: (cache_file, data_file, item_name, section, key, cache_field)
updates = [
    # CHASSIS updates
    ('chassis_cache.json', 'Chassis_data', 'Ranger', 'Base Stats', 'Armor', 'armor'),
    ('chassis_cache.json', 'Chassis_data', 'Ranger', 'Base Stats', 'Speed', 'speed'),
    ('chassis_cache.json', 'Chassis_data', 'Ranger', 'Base Stats', 'Critical Hit Chance', 'critical_hit_chance'),
    ('chassis_cache.json', 'Chassis_data', 'Overseer', 'Base Stats', 'Armor', 'armor'),
    ('chassis_cache.json', 'Chassis_data', 'Overseer', 'Base Stats', 'Speed', 'speed'),
    ('chassis_cache.json', 'Chassis_data', 'Sentinel', 'Base Stats', 'Armor', 'armor'),
    ('chassis_cache.json', 'Chassis_data', 'Reaper', 'Base Stats', 'Armor', 'armor'),
    ('chassis_cache.json', 'Chassis_data', 'Reaper', 'Base Stats', 'Speed', 'speed'),
    ('chassis_cache.json', 'Chassis_data', 'Bulwark', 'Base Stats', 'Armor', 'armor'),
    ('chassis_cache.json', 'Chassis_data', 'Bulwark', 'Base Stats', 'Speed', 'speed'),
    ('chassis_cache.json', 'Chassis_data', 'Marauder', 'Base Stats', 'Speed', 'speed'),
    ('chassis_cache.json', 'Chassis_data', 'Marauder', 'Base Stats', 'Critical Hit Chance', 'critical_hit_chance'),
    ('chassis_cache.json', 'Chassis_data', 'Leviathan', 'Base Stats', 'Speed', 'speed'),
    ('chassis_cache.json', 'Chassis_data', 'Leviathan', 'Base Stats', 'Critical Hit Chance', 'critical_hit_chance'),
    ('chassis_cache.json', 'Chassis_data', 'CyCorps Overseer', 'Base Stats', 'Speed', 'speed'),
    ('chassis_cache.json', 'Chassis_data', 'Enhanced Reaper', 'Base Stats', 'Critical Hit Chance', 'critical_hit_chance'),
    ('chassis_cache.json', 'Chassis_data', 'Flaming Hornet', 'Base Stats', 'Critical Hit Chance', 'critical_hit_chance'),
    ('chassis_cache.json', 'Chassis_data', 'Flaming Orbiter', 'Base Stats', 'Critical Hit Chance', 'critical_hit_chance'),
    ('chassis_cache.json', 'Chassis_data', 'Hornet', 'Base Stats', 'Critical Hit Chance', 'critical_hit_chance'),
    ('chassis_cache.json', 'Chassis_data', 'Recon Hornet', 'Base Stats', 'Critical Hit Chance', 'critical_hit_chance'),
    ('chassis_cache.json', 'Chassis_data', 'Recon Warthog', 'Base Stats', 'Critical Hit Chance', 'critical_hit_chance'),
    ('chassis_cache.json', 'Chassis_data', 'Terminus Prototype', 'Base Stats', 'Critical Hit Chance', 'critical_hit_chance'),
    ('chassis_cache.json', 'Chassis_data', 'Viper', 'Base Stats', 'Critical Hit Chance', 'critical_hit_chance'),
    ('Orbiter', 'Base Stats', 'Critical Hit Chance', 'critical_hit_chance'),
    ('Valadin', 'Base Stats', 'Critical Hit Chance', 'critical_hit_chance'),
    ('Crusader', 'Base Stats', 'Critical Hit Chance', 'critical_hit_chance'),
    
    # SHIELDS updates  
    ('shields_cache.json', 'Shields_data', 'Photonic SV', 'Properties', 'Recharge Rate', 'recharge_rate'),
    ('shields_cache.json', 'Shields_data', 'Photonic DV', 'Properties', 'Recharge Rate', 'recharge_rate'),
    ('shields_cache.json', 'Shields_data', 'Photonic Sphere', 'Properties', 'Energy Use', 'energy_use'),
    ('shields_cache.json', 'Shields_data', 'Argon Array', 'Properties', 'Recharge Rate', 'recharge_rate'),
]

print("Note: This script requires manual implementation due to complex regex patterns.")
print("\nKey changes needed:")
print("\nCHASSIS_DATA:")
for cache_f, data_f, item, sect, key, cache_key in updates:
    if cache_f == 'chassis_cache.json':
        with open(cache_f) as f:
            cache = json.load(f)
        if item in cache:
            val = cache[item].get(cache_key)
            print(f"  {item} - {key}: update to {val}")

print("\nSHIELDS_DATA:")
for cache_f, data_f, item, sect, key, cache_key in updates:
    if cache_f == 'shields_cache.json':
        with open(cache_f) as f:
            cache = json.load(f)
        if item in cache:
            val = cache[item].get(cache_key)
            print(f"  {item} - {key}: update to {val}")

print("\nMODULES_DATA:")
with open('modules_cache.json') as f:
    modules = json.load(f)
modules_updates = [
    ('Anomaly Detector', 'merit'),
    ('Security Countermand', 'merit'),
    ('ComWave Scanner', 'merit'),
]
for item, key in modules_updates:
    if item in modules:
        print(f"  {item} - Defensive Merit: update to {modules[item].get('merit')}")

print("\nREACTORS_DATA:")
with open('reactors_cache.json') as f:
    reactors = json.load(f)
if 'True Guard Cell' in reactors:
    print(f"  True Guard Cell - Max Energy Level: update to {reactors['True Guard Cell'].get('max_power')}")
    print(f"  True Guard Cell - Recharge Rate: update to {reactors['True Guard Cell'].get('recharge_rate')}")
    print(f"  True Guard Cell - Defensive Merit: update to {reactors['True Guard Cell'].get('merit')}")

print("\nWEAPONS_DATA:")
with open('weapons_cache.json') as f:
    weapons = json.load(f)
weapons_updates = [
    ('Good Samaritan', 'Shield Damage', 'shield_damage'),
]
for item, key, cache_key in weapons_updates:
    if item in weapons:
        val = weapons[item].get(cache_key)
        print(f"  {item} - {key}: update to {val}")
