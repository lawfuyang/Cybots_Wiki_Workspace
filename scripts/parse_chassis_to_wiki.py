#!/usr/bin/env python3
"""Generate a Fandom Wikitext table from chassis_data.json.

This version flattens every property into its own column so each
sub-property (e.g. `Unit Type`, `Chassis Cost`, `Weapon Slots`,
`Weapon Tech`, `Payload`, etc.) becomes a separate table column.

Output file: chassis_table.wiki (in workspace root)
"""
import json
import os
from typing import Any, Dict, List


def format_value(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, dict):
        # Common pattern: {"value": ..., "unit": ...}
        if "value" in v and "unit" in v:
            val = v.get("value")
            unit = v.get("unit")
            if val is None:
                return str(unit) if unit is not None else ""
            if unit is None or unit == "":
                return str(val)
            return f"{val} {unit}"
        # Otherwise join sub-keys with semicolon
        parts: List[str] = []
        for k, subv in v.items():
            subval = format_value(subv)
            if subval:
                parts.append(f"{k}: {subval}")
            else:
                parts.append(f"{k}:")
        return "; ".join(parts)
    if isinstance(v, (list, tuple)):
        return ", ".join(format_value(x) for x in v)
    return str(v)


def collect_subkeys(data: List[Dict]) -> Dict[str, List[str]]:
    sections_order = [
        "Unit Information",
        "Slots",
        "Starting Tech Levels",
        "Base Stats",
        "Unique Stats",
        "Hidden Stats",
    ]
    subkeys: Dict[str, List[str]] = {s: [] for s in sections_order}
    for entry in data:
        sections = entry.get("sections", {}) or {}
        for s in sections_order:
            sec = sections.get(s, {}) or {}
            for k in sec.keys():
                if k not in subkeys[s]:
                    subkeys[s].append(k)
    return subkeys


def escape_pipes(text: str) -> str:
    return text.replace("|", "&#124;")


def main():
    src = os.path.join(os.getcwd(), "chassis_data.json")
    out_path = os.path.join(os.getcwd(), "chassis_table.wiki")
    with open(src, "r", encoding="utf-8") as f:
        data = json.load(f)

    sections_order = [
        "Unit Information",
        "Slots",
        "Starting Tech Levels",
        "Base Stats",
        "Unique Stats",
        "Hidden Stats",
    ]

    subkeys_map = collect_subkeys(data)

    # Build header columns: Image, Name, then each subkey (in section order)
    header_cols: List[str] = ["Image", "Name"]
    for sec in sections_order:
        for k in subkeys_map.get(sec, []):
            header_cols.append(k)

    lines: List[str] = []
    lines.append('{| class="wikitable sortable" style="width:100%;"')
    lines.append('|+ Chassis overview')
    header = '!' + ' !! '.join(header_cols)
    lines.append('|-')
    lines.append(header)

    for entry in data:
        title = entry.get('title', '')
        url = entry.get('url') or ''
        if url:
            name_cell = f'[{url} {title}]'
        else:
            name_cell = title

        row_cells: List[str] = []
        # image blank for now
        row_cells.append("")
        row_cells.append(name_cell)

        sections = entry.get('sections', {}) or {}
        for sec in sections_order:
            sec_dict = sections.get(sec, {}) or {}
            for k in subkeys_map.get(sec, []):
                val = sec_dict.get(k)
                cell = format_value(val)
                cell = escape_pipes(cell)
                row_cells.append(cell)

        row = '| ' + ' || '.join(row_cells)
        lines.append('|-')
        lines.append(row)

    lines.append('|}')

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"Wikitext written to: {out_path}")


if __name__ == '__main__':
    main()
