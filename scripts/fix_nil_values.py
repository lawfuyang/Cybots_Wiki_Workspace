#!/usr/bin/env python3
"""
Fix remaining discrepancies - replace 0 with nil where cache has None
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

def set_to_nil(entry_text, key):
    """Set a value to nil"""
    # Pattern: ["Key"] = 0 or ["Key"] = { value = 0, unit = ... }
    
    # Simple pattern first
    simple_pattern = rf'(\["{re.escape(key)}"\]\s*=\s*)0'
    simple_match = re.search(simple_pattern, entry_text)
    
    if simple_match:
        old_text = simple_match.group(0)
        new_text = f'["{key}"] = nil'
        new_entry = entry_text.replace(old_text, new_text)
        return new_entry, True
    
    return entry_text, False

def update_file(filepath, updates_list):
    """Apply all updates to a file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    for item_name, key in updates_list:
        entry_text, positions = find_entry_by_title(content, item_name)
        
        if entry_text is None:
            print(f"  ERROR: Could not find entry: {item_name}")
            continue
        
        new_entry, changed = set_to_nil(entry_text, key)
        
        if changed:
            start, end = positions
            content = content[:start] + new_entry + content[end:]
            print(f"  ✓ Set {item_name}.{key} to nil")
        else:
            print(f"  ✗ Could not set: {item_name}.{key}")
    
    return content

# Weapons - set to nil
print("Updating Weapons_data.wikitext...")
weapons_updates = [
    ('EM Syphon', 'Shield Damage'),
    ('EM Syphon', 'Armor Piercing'),
    ('Syphon MKII', 'Shield Damage'),
    ('Syphon MKII', 'Armor Piercing'),
    ('Syphon Elite', 'Shield Damage'),
    ('Syphon Elite', 'Armor Piercing'),
    ('Syphonic Disruptor', 'Shield Damage'),
    ('Syphonic Disruptor', 'Armor Piercing'),
    ('Syphon Immobiliser', 'Shield Damage'),
    ('Syphon Immobiliser', 'Armor Piercing'),
    ('G33 Launcher', 'Armor Piercing'),
    ('Heavy Shield Disruptor', 'Armor Piercing'),
    ('Shield Displacer', 'Armor Piercing'),
    ('Pulse Beam', 'Armor Piercing'),
    ('Shield Neutraliser', 'Armor Piercing'),
    ('Magnatron', 'Armor Piercing'),
    ('Pulse Streamer', 'Armor Piercing'),
]
weapons_content = update_file('cybots_wiki/pages/Module/Weapons_data.wikitext', weapons_updates)
with open('cybots_wiki/pages/Module/Weapons_data.wikitext', 'w', encoding='utf-8') as f:
    f.write(weapons_content)

print("\nUpdating Modules_data.wikitext...")
modules_updates = [
    ('Motion Tracker', 'Defensive Merit'),
    ('Storm Shield', 'Defensive Merit'),
]
modules_content = update_file('cybots_wiki/pages/Module/Modules_data.wikitext', modules_updates)
with open('cybots_wiki/pages/Module/Modules_data.wikitext', 'w', encoding='utf-8') as f:
    f.write(modules_content)

print("\nDone!")
