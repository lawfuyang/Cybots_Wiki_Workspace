"""
Add image1 to Enemies_data entries that are missing it.
Assignment priority:
  1. Explicit CHASSIS_IMAGE_MAP (chassis type -> image)
  2. Skip if no mapping exists (leave without image1 rather than guess wrongly)
"""
import re
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent

# Explicit chassis -> image mapping
# Overrides based on: existing enemies (representative ones) + Chassis_data
CHASSIS_IMAGE_MAP = {
    # Usable chassis with known images
    "Ranger":                 "Ranger.jpeg",
    "Valadin XR":             "Valadin.jpg",       # Valadin XR ≈ Valadin chassis
    "Tomb Seal":              "Terrain1.png",
    "Radial Laser Turret":    "Turret2.png",
    "Scaven Gang":            "Scavengrenadiers.jpg",
    "Scaven Commander":       "Scavenboss.jpg",
    "Overseer":               "Hover.png",          # Override: enemies use Hover.png, not Overseer.jpg
    "Reaper":                 "Spider.png",          # Override: enemies use Spider.png, not Reaper.jpg
    "CyCorps Overseer":       "Cycorps_overseer.jpg",
    "CyCorps Orbiter":        "Cyorbiter.jpg",
    "CyCorps Ranger":         "Cyranger.jpg",
    "CyCorps Reaper":         "Cycorps_reaper.jpg",
    "CyCorps Valadin":        "Cyvaladin.jpg",
    "CyCorps Marauder":       "Cymarauder.jpg",
    "CyCorps Leviathan":      "Cycorps_leviathan.jpg",
    "Disruptor Tank":         "Tank_disruptor.png",
    "Super Heavy Tank":       "Tank_super.png",
    "TR-90x Goshawk":         "Jetfighter.png",
    # Chassis with no existing images in Enemies_data -> will be skipped (no entry)
}

enemies_path = WORKSPACE / "cybots_wiki/pages/Module/Enemies_data.wikitext"
lines = enemies_path.read_text(encoding="utf-8").splitlines(keepends=True)

TITLE_RE   = re.compile(r'^\s+title = "([^"]+)"')
IMAGE1_RE  = re.compile(r'^\s+image1 = ')
CHASSIS_RE = re.compile(r'^\s+chassis = ')

new_lines = []
i = 0
changed = 0
skipped = 0

while i < len(lines):
    line = lines[i]

    # Detect start of a top-level entry block
    t = TITLE_RE.match(line)
    if t:
        entry_title = t.group(1)
        # Peek ahead to find chassis name and check for image1
        # Collect lines of this entry until we hit the next top-level entry or end
        entry_start = i
        j = i + 1
        has_image1 = False
        chassis_name = None
        # Scan ahead at most 30 lines to find chassis and image1 within this block
        while j < min(i + 50, len(lines)):
            lj = lines[j]
            if IMAGE1_RE.match(lj):
                has_image1 = True
                break
            cm = re.match(r'^\s+chassis = \{\s*name = "([^"]+)"', lj)
            if cm:
                chassis_name = cm.group(1)
            # Stop scanning at next top-level entry (title line at same indent)
            if j > i + 2 and TITLE_RE.match(lj):
                break
            j += 1

        if not has_image1 and chassis_name:
            img = CHASSIS_IMAGE_MAP.get(chassis_name)
            if img:
                new_lines.append(line)  # title line
                new_lines.append(f'        image1 = "{img}",\n')
                changed += 1
                print(f"  ADD  [{entry_title}] chassis={chassis_name!r} => {img!r}")
                i += 1
                continue
            else:
                skipped += 1
                # print(f"  SKIP [{entry_title}] chassis={chassis_name!r} (no image map)")

    new_lines.append(line)
    i += 1

enemies_path.write_text("".join(new_lines), encoding="utf-8")
print(f"\n  => Added image1 to {changed} entries ({skipped} left without image)")
