#!/usr/bin/env python3
"""
Update Cybots Wiki data files - handles nil values
"""
import json
import re

def find_entry_by_title(content, title):
    """Find and return a complete entry by title"""
    pattern = rf'title\s*=\s*"{re.escape(title)}"'
    match = re.search(pattern, content)
    if not match:
        return None, None
    
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
    new_val_str = str(new_value)
    
    # Pattern 1: Replace nil values
    nil_pattern = rf'(\["{re.escape(key)}"\]\s*=\s*)(nil)'
    nil_match = re.search(nil_pattern, entry_text)
    
    if nil_match:
        old_text = nil_match.group(0)
        new_text = f'["{key}"] = {new_val_str}'
        new_entry = entry_text.replace(old_text, new_text)
        return new_entry, True
    
    # Pattern 2: Simple numeric value like ["Key"] = 123
    simple_pattern = rf'(\["{re.escape(key)}"\]\s*=\s*)(\d+(?:\.\d+)?)'
    simple_match = re.search(simple_pattern, entry_text)
    
    if simple_match:
        old_text = simple_match.group(0)
        new_text = f'["{key}"] = {new_val_str}'
        new_entry = entry_text.replace(old_text, new_text)
        return new_entry, True
    
    # Pattern 3: Complex value like ["Key"] = { value = 123, unit = "%" }
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
            print(f"  ✗ Could not find/update: {item_name}/{section}/{key}")
    
    return content

# Load cache files
with open('reactors_cache.json') as f:
    reactors_cache = json.load(f)

# Reactors updates for True Guard Cell
print("Updating Reactors_data.wikitext...")
reactors_updates = [
    ('True Guard Cell', 'Properties', 'Max Energy Level', reactors_cache['True Guard Cell']['max_power']),
    ('True Guard Cell', 'Properties', 'Recharge Rate', reactors_cache['True Guard Cell']['recharge_rate']),
    ('True Guard Cell', 'Properties', 'Defensive Merit', reactors_cache['True Guard Cell']['merit']),
]
reactors_content = update_file('cybots_wiki/pages/Module/Reactors_data.wikitext', reactors_updates)
with open('cybots_wiki/pages/Module/Reactors_data.wikitext', 'w', encoding='utf-8') as f:
    f.write(reactors_content)

print("Done!")
