import json
import re
import os

def extract_lua_simple(lua_text):
    """Simple extraction of key properties from Lua"""
    items = {}
    
    # Find all entries (title = ..., url = ..., etc.)
    entry_pattern = r'\{\s*title\s*=\s*"([^"]+)"'
    for match in re.finditer(entry_pattern, lua_text):
        title = match.group(1)
        # Find the section from this title to the next closing brace
        start = match.start()
        brace_depth = 0
        end = start
        found_open = False
        for i in range(start, len(lua_text)):
            if lua_text[i] == '{':
                brace_depth += 1
                found_open = True
            elif lua_text[i] == '}' and found_open:
                brace_depth -= 1
                if brace_depth == 0:
                    end = i + 1
                    break
        
        entry_text = lua_text[start:end]
        items[title] = entry_text
    
    return items

def extract_property_value(text, key):
    """Extract a property value from Lua text"""
    # Pattern for the key with value
    pattern = rf'\["{key}"\]\s*=\s*([^,\n}}]+)'
    match = re.search(pattern, text)
    if match:
        val_str = match.group(1).strip()
        # Handle {value, unit} pattern
        if val_str.startswith('{'):
            val_match = re.search(r'value\s*=\s*([\d.]+)', val_str)
            unit_match = re.search(r'unit\s*=\s*"([^"]+)"', val_str)
            if val_match:
                num = int(val_match.group(1)) if '.' not in val_match.group(1) else float(val_match.group(1))
                if unit_match:
                    return f"{num} {unit_match.group(1)}"
                return num
        # Handle simple numeric or string
        if val_str == 'nil':
            return None
        elif val_str.replace('.', '', 1).isdigit():
            return int(val_str) if '.' not in val_str else float(val_str)
        elif val_str.startswith('"') and val_str.endswith('"'):
            return val_str[1:-1]
        return val_str
    return None

# Item type mappings: (cache_type, cache_field_name, data_file, lua_section, lua_field)
comparisons = [
    ('chassis', 'armor', 'Chassis_data', 'Base Stats', 'Armor'),
    ('chassis', 'speed', 'Chassis_data', 'Base Stats', 'Speed'),
    ('chassis', 'critical_hit_chance', 'Chassis_data', 'Base Stats', 'Critical Hit Chance'),
    ('weapons', 'merit', 'Weapons_data', 'Properties', 'Offensive Merit'),
    ('weapons', 'shield_damage', 'Weapons_data', 'Properties', 'Shield Damage'),
    ('weapons', 'armor_damage', 'Weapons_data', 'Properties', 'Armor Piercing'),
    ('modules', 'merit', 'Modules_data', 'Properties', 'Defensive Merit'),
    ('modules', 'energy_use', 'Modules_data', 'Properties', 'Energy Use'),
    ('reactors', 'merit', 'Reactors_data', 'Properties', 'Defensive Merit'),
    ('reactors', 'max_power', 'Reactors_data', 'Properties', 'Max Energy Level'),
    ('reactors', 'recharge_rate', 'Reactors_data', 'Properties', 'Recharge Rate'),
    ('shields', 'merit', 'Shields_data', 'Properties', 'Defensive Merit'),
    ('shields', 'energy_use', 'Shields_data', 'Properties', 'Energy Use'),
    ('shields', 'recharge_rate', 'Shields_data', 'Properties', 'Recharge Rate'),
]

issues = []

for cache_type, cache_field, data_file_name, lua_section, lua_field in comparisons:
    cache_file = f"{cache_type}_cache.json"
    data_file = f"cybots_wiki/pages/Module/{data_file_name}.wikitext"
    
    if not os.path.exists(cache_file) or not os.path.exists(data_file):
        continue
    
    with open(cache_file) as f:
        cache_data = json.load(f)
    
    with open(data_file) as f:
        lua_text = f.read()
    
    lua_items = extract_lua_simple(lua_text)
    
    for item_name, cache_val in cache_data.items():
        cache_value = cache_val.get(cache_field)
        
        if item_name not in lua_items:
            continue
        
        lua_entry = lua_items[item_name]
        lua_value = extract_property_value(lua_entry, lua_field)
        
        if cache_value != lua_value:
            issues.append({
                'type': cache_type,
                'item': item_name,
                'field': lua_field,
                'cache_value': cache_value,
                'lua_value': lua_value,
                'file': data_file_name
            })

# Print results
if issues:
    print(f"Found {len(issues)} discrepancies:\n")
    for issue in issues:
        print(f"{issue['type'].upper()} - {issue['item']}")
        print(f"  Field: {issue['field']}")
        print(f"  Cache: {issue['cache_value']} | Lua: {issue['lua_value']}")
        print()
else:
    print("No discrepancies found!")
