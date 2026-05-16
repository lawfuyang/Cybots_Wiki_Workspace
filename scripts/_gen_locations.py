"""Generate LOCATIONS Lua table for Module:Enemies"""
import json, re

with open('d:/Workspace/Cybots_Wiki_Workspace/REFERENCES/enemies_cache.json') as f:
    cache = json.load(f)

# Build name -> sorted unique locations
loc_map = {}
for name, data in cache.items():
    locs = sorted(set(data.get('locations_found', [])))
    if locs:
        loc_map[name] = locs

# Fix known typo: cache "Scaen Grenadiers" == data module "Scaven Grenadiers"
if 'Scaen Grenadiers' in loc_map:
    loc_map['Scaven Grenadiers'] = loc_map.pop('Scaen Grenadiers')

# Read data module to get all entry titles
with open('d:/Workspace/Cybots_Wiki_Workspace/cybots_wiki/pages/Module/Enemies_data.wikitext') as f:
    dm = f.read()

titles = re.findall(r'title\s*=\s*"([^"]+)"', dm)

# Case-insensitive match for any remaining unmatched titles
titles_lower = {t.lower(): t for t in titles}
resolved = {}
for cache_name, locs in list(loc_map.items()):
    if cache_name in titles:
        resolved[cache_name] = locs
    elif cache_name.lower() in titles_lower:
        dm_title = titles_lower[cache_name.lower()]
        resolved[dm_title] = locs
        print(f'Case-matched: cache {repr(cache_name)} -> dm {repr(dm_title)}')
    else:
        print(f'No match in DM: {repr(cache_name)}')

# Generate Lua LOCATIONS table
lines = []
lines.append('-- Location lookup: entry title -> array of locations')
lines.append('-- Sourced from enemies_cache.json locations_found field')
lines.append('local LOCATIONS = {')

# Order: Vulcore entries first, then Talsian, then Gamma, then multi-location
def sort_key(item):
    name, locs = item
    loc_str = ','.join(locs)
    order = {'Vulcore': 0, 'Talsian Warfront': 1, 'Gamma Sector': 2}
    min_order = min(order.get(l, 3) for l in locs)
    is_multi = 1 if len(locs) > 1 else 0
    return (is_multi, min_order, name)

for name, locs in sorted(resolved.items(), key=sort_key):
    locs_str = ', '.join(f'"{l}"' for l in locs)
    escaped = name.replace('"', '\\"')
    lines.append(f'    ["{escaped}"] = {{{locs_str}}},')

lines.append('}')

lua_table = '\n'.join(lines)
print('\n\n=== LUA TABLE ===')
print(lua_table)

with open('d:/Workspace/Cybots_Wiki_Workspace/scripts/_locations_table.lua', 'w') as f:
    f.write(lua_table)
print('\n\nWritten to scripts/_locations_table.lua')
