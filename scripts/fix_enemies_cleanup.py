"""Cleanup corrupted Enemies_data.wikitext caused by bad regex on url() calls."""
import re
from pathlib import Path

path = Path(__file__).parent.parent / "cybots_wiki/pages/Module/Enemies_data.wikitext"
text = path.read_text(encoding="utf-8")

# Fix corruption: the old regex [^)]* stopped at first ')' inside argument strings
# like url("Baron_(Shield)"), leaving behind  "") }  artifacts.
# The artifact looks like:  { name = "Baron"") },
# Fix: remove the leftover  ") that appears right after a closing quote that follows name = "...
text = re.sub(r'""\)', '"', text)

# Also remove any remaining url = url(...) lines that weren't cleaned
text = re.sub(r',\s*url = url\("[^"]*"\)', '', text)
text = re.sub(r'^        url = url\("[^"]*"\),\n', '', text, flags=re.MULTILINE)

path.write_text(text, encoding="utf-8")
print("Done. Remaining url references:")
for i, line in enumerate(text.splitlines(), 1):
    if "url = url" in line:
        print(f"  Line {i}: {line.strip()}")
print("Remaining 'local function url' references:")
for i, line in enumerate(text.splitlines(), 1):
    if "local function url" in line:
        print(f"  Line {i}: {line.strip()}")
