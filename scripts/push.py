import argparse
import difflib
import json
import os
import subprocess
import time

import pywikibot

# ----------------------------------------
# CONFIG
# ----------------------------------------

PAGES_DIR = "cybots_wiki"
METADATA_DIR = "metadata"

EDIT_SUMMARY = "Bulk local sync"

RATE_LIMIT_SECONDS = 2


# ----------------------------------------
# ARGUMENTS
# ----------------------------------------

parser = argparse.ArgumentParser()

parser.add_argument(
    "--dry-run",
    action="store_true",
    help="Show what would upload without saving"
)

parser.add_argument(
    "--show-diff",
    action="store_true",
    help="Show unified diffs"
)

args = parser.parse_args()


# ----------------------------------------
# CONNECT TO WIKI
# ----------------------------------------

site = pywikibot.Site("en", "cybots")


# ----------------------------------------
# GET FILES FROM LAST COMMIT
# ----------------------------------------

result = subprocess.run(
    [
        "git",
        "diff-tree",
        "--no-commit-id",
        "--name-only",
        "-r",
        "HEAD"
    ],
    capture_output=True,
    text=True
)

changed_files = [
    f.strip()
    for f in result.stdout.splitlines()
    if f.startswith(f"{PAGES_DIR}/")
    and f.endswith(".wikitext")
]

if not changed_files:
    print("No wikitext pages changed in the last commit.")
    exit(0)

print("Files from last commit:")
for f in changed_files:
    print(f"  - {f}")


# ----------------------------------------
# PROCESS FILES
# ----------------------------------------

for filepath in changed_files:

    filename = os.path.basename(filepath)

    # Remove .wiki extension
    title = filename[:-5]

    # Convert underscores back to slashes
    title = title.replace("_", "/")

    print("=" * 60)
    print(f"PAGE: {title}")

    # ----------------------------------------
    # LOAD LOCAL TEXT
    # ----------------------------------------

    with open(filepath, encoding="utf-8") as f:
        local_text = f.read()

    # ----------------------------------------
    # LOAD REMOTE PAGE
    # ----------------------------------------

    page = pywikibot.Page(site, title)

    try:
        remote_text = page.text
    except Exception as e:
        print(f"Failed to fetch page: {e}")
        continue

    # ----------------------------------------
    # SKIP IF IDENTICAL
    # ----------------------------------------

    if local_text == remote_text:
        print("No actual content changes.")
        continue

    # ----------------------------------------
    # OPTIONAL REVISION CONFLICT CHECK
    # ----------------------------------------

    metadata_path = os.path.join(
        METADATA_DIR,
        filename.replace(".wiki", ".json")
    )

    if os.path.exists(metadata_path):

        with open(metadata_path, encoding="utf-8") as f:
            metadata = json.load(f)

        stored_revid = metadata.get("revid")

        if stored_revid:

            remote_revid = page.latest_revision_id

            if remote_revid != stored_revid:
                print("WARNING: Revision conflict detected!")
                print(f"Stored revision: {stored_revid}")
                print(f"Current revision: {remote_revid}")
                print("Skipping.")
                continue

    # ----------------------------------------
    # SHOW DIFF
    # ----------------------------------------

    if args.show_diff:

        diff = difflib.unified_diff(
            remote_text.splitlines(),
            local_text.splitlines(),
            fromfile="remote",
            tofile="local",
            lineterm=""
        )

        print("\n".join(diff))

    # ----------------------------------------
    # DRY RUN
    # ----------------------------------------

    if args.dry_run:
        print("[DRY RUN] Would upload.")
        continue

    # ----------------------------------------
    # UPLOAD
    # ----------------------------------------

    try:

        page.text = local_text

        page.save(
            summary=EDIT_SUMMARY,
            minor=False
        )

        print("Uploaded successfully.")

    except Exception as e:
        print(f"Upload failed: {e}")
        continue

    # ----------------------------------------
    # RATE LIMIT
    # ----------------------------------------

    time.sleep(RATE_LIMIT_SECONDS)

print("=" * 60)
print("Done.")