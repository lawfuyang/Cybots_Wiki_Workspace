#!/usr/bin/env python3
import re
from pathlib import Path

p = Path('cybots_wiki/pages/Module/Enemies_data.wikitext')
text = p.read_text(encoding='utf-8')
lines = text.splitlines()

mapping = {
    "Valadin XR": "Enemy_walker.png",
    "Marauder": "Enemy_quadra.png",
    "Overseer": "Enemy_hover.png",
    "Ranger": "Enemy_trike.png",
    "Reaper": "Enemy_spider.png",
    "Sentinel": "Enemy_tracker.png",
}

# Remove the runtime mapping block if present
start = None
end = None
for idx, line in enumerate(lines):
    if 'local chassis_image_map' in line:
        start = idx
        break
if start is not None:
    for j in range(start, len(lines)):
        if lines[j].strip() == 'return data':
            end = j
            break
if start is not None and end is not None:
    del lines[start:end+1]
    while start-1 >= 0 and lines[start-1].strip()== '':
        del lines[start-1]
        start -= 1

# Revert header `local data = {` -> `return {`
for idx, line in enumerate(lines):
    if line.strip().startswith('local data = {'):
        lines[idx] = line.replace('local data = {', 'return {', 1)
        break

# Walk file and update or insert image1 lines for matching chassis
i = 0
while i < len(lines):
    line = lines[i]
    m = re.search(r'chassis\s*=\s*{\s*name\s*=\s*"(.*?)"\s*},', line)
    if m:
        c = m.group(1)
        if c in mapping:
            # search backwards up to 6 lines for an image1 line
            j = i-1
            found_img = False
            while j >= 0 and j >= i-6:
                if 'image1' in lines[j]:
                    lines[j] = re.sub(r'image1\s*=\s*".*?"', f'image1 = "{mapping[c]}"', lines[j])
                    found_img = True
                    break
                if lines[j].strip() == '':
                    j -= 1
                    continue
                if 'title' in lines[j] or 'title =' in lines[j]:
                    break
                j -= 1
            if not found_img:
                indent = re.match(r'^(\s*)', line).group(1)
                lines.insert(i, f'{indent}image1 = "{mapping[c]}",')
                i += 1
    i += 1

p.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print('Updated', p)
