#!/usr/bin/env python3
import json
import re

with open('chassis_cache.json') as f:
    cache = json.load(f)

with open('cybots_wiki/pages/Module/Chassis_data.wikitext') as f:
    content = f.read()

# Map cache values to expected percentage integers
expected = {}
for name, data in cache.items():
    if 'critical_hit_chance' in data:
        val = data['critical_hit_chance']
        if val < 1:
            expected[name] = int(val * 100)
        else:
            expected[name] = int(val)

# Extract critical hit chance values from Lua
mismatches = []
for name in expected:
    pattern = rf'title\s*=\s*"{re.escape(name)}"[^}}]*\[\s*"Critical Hit Chance"\s*\]\s*=\s*{{[^}}]*value\s*=\s*(\d+)'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        lua_val = int(match.group(1))
        if lua_val != expected[name]:
            mismatches.append(f"{name}: cache={data['critical_hit_chance']}, expected={expected[name]}%, found={lua_val}%")

if mismatches:
    print("Mismatches found:")
    for m in mismatches:
        print(f"  {m}")
else:
    print("✓ All Critical Hit Chance values are correct!")
