import json

with open('cybots_wiki/allimages.json') as f:
    names = {img['name'].lower(): img['name'] for img in json.load(f)['allimages']}

nil_modules = [
    'Phase Modulator', 'Credit Bank', 'Leadership', 'BM Adjustment',
    'Advanced Computer Systems', 'Light Wall Effect', 'Inspiration',
    'EM Repulsor Field', 'Voltage Conveyer', 'Omega Pathfinder', 'Gunnery Metalink',
    'Horus Fire of Ra', 'Horus moon of Ra', 'Horus Ice of Ra', 'Horus Sun of Ra',
]
for m in nil_modules:
    slug  = m.lower().replace(' ', '')
    slug2 = m.lower().replace(' ', '_')
    r1 = names.get(slug + '.jpg') or names.get(slug + '.png')
    r2 = names.get(slug2 + '.jpg') or names.get(slug2 + '.png')
    print(f'{m}: slug={r1}, slug2={r2}')
