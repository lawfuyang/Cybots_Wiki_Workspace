import json, re

with open('d:/Workspace/Cybots_Wiki_Workspace/REFERENCES/enemies_cache.json') as f:
    cache = json.load(f)

loc_map = {}
for name, data in cache.items():
    locs = sorted(set(data.get('locations_found', [])))
    if locs:
        loc_map[name] = locs

with open('d:/Workspace/Cybots_Wiki_Workspace/cybots_wiki/pages/Module/Enemies_data.wikitext') as f:
    dm = f.read()

titles = re.findall(r'title\s*=\s*"([^"]+)"', dm)
print(f'Data module titles: {len(titles)}')

no_loc = [t for t in titles if t not in loc_map]
print(f'No location in cache: {len(no_loc)}')
for t in no_loc[:30]:
    print(f'  missing: {repr(t)}')

not_in_dm = [n for n in loc_map if n not in titles]
print(f'\nCache entries not in data module: {len(not_in_dm)}')
for n in not_in_dm:
    print(f'  cache only: {repr(n)}')
