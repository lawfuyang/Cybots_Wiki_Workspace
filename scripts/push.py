import subprocess
import os
import pywikibot

site = pywikibot.Site('en', 'fandom')
site.lang = 'cybots'

# Get changed files from git
result = subprocess.run(
    ["git", "diff", "--name-only"],
    capture_output=True,
    text=True
)

changed_files = [
    f for f in result.stdout.strip().split("\n")
    if f.startswith("pages/") and f.endswith(".wikitext")
]

for filepath in changed_files:

    filename = os.path.basename(filepath)

    # Convert filename back to wiki title
    title = filename[:-5].replace("_", "/")

    with open(filepath, encoding="utf-8") as f:
        text = f.read()

    page = pywikibot.Page(site, title)

    # Safety check
    if page.text != text:
        print(f"Uploading: {title}")

        page.text = text

        page.save(
            summary="Bulk local edit sync",
            minor=False
        )