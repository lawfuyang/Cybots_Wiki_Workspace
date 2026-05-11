import pywikibot
import os
import time
from urllib.parse import unquote
from concurrent.futures import ThreadPoolExecutor, as_completed

site = pywikibot.Site()
base_dir = "cybots_wiki"

pages_dir = os.path.join(base_dir, "pages")
files_dir = os.path.join(base_dir, "files")
os.makedirs(pages_dir, exist_ok=True)
os.makedirs(files_dir, exist_ok=True)

def sanitize_title(title):
    title = title.replace(" ", "_").replace("/", "_").replace("\\", "_").replace(":", "_")
    return unquote(title)[:220]

def get_namespace_folder(ns_id):
    if ns_id == 0:
        return "Main"
    try:
        ns = site.namespaces[ns_id]
        name = ns.custom_name or ns.name
        return name.replace(" ", "_")
    except:
        return f"NS_{ns_id}"

def download_page(page):
    try:
        ns_folder = get_namespace_folder(page.namespace())
        clean_title = sanitize_title(page.title(with_ns=False))
        
        folder = os.path.join(pages_dir, ns_folder)
        os.makedirs(folder, exist_ok=True)
        
        filepath = os.path.join(folder, f"{clean_title}.wikitext")
        
        if os.path.exists(filepath):
            return f"✓ Skipped: {page.title()}"
        
        text = page.text
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text)
        
        return f"✓ Saved: {page.title()}"
    except Exception as e:
        return f"✗ Failed {page.title()}: {e}"

def download_file(filepage):
    try:
        fp = pywikibot.FilePage(filepage)
        original_name = fp.title(with_ns=False)
        clean_name = sanitize_title(original_name)
        
        if '.' not in clean_name:
            try:
                url = fp.get_file_url()
                ext = os.path.splitext(url)[1].lower()
                if ext:
                    clean_name += ext
            except:
                pass
        
        filepath = os.path.join(files_dir, clean_name)
        
        if os.path.exists(filepath):
            return f"✓ Skipped file: {clean_name}"
        
        print(f"Downloading: {clean_name}")
        success = fp.download(filepath)
        
        if success and os.path.exists(filepath):
            return f"✓ Saved file: {clean_name}"
        else:
            return f"✗ Failed file: {clean_name}"
    except Exception as e:
        return f"✗ Error file {filepage.title()}: {e}"

# ====================== MAIN ======================
print(f"Mirroring {site}...\n")

print("=== Downloading pages from ALL valid namespaces ===")

with ThreadPoolExecutor(max_workers=6) as executor:
    futures = []
    
    for ns_id in site.namespaces:
        if ns_id < 0:                     # Skip Media (-2), Special (-1), etc.
            continue
            
        ns_name = get_namespace_folder(ns_id)
        print(f"→ Fetching namespace: {ns_name} (ID: {ns_id})")
        
        try:
            pages = list(site.allpages(namespace=ns_id))
            for page in pages:
                futures.append(executor.submit(download_page, page))
        except Exception as e:
            print(f"   ✗ Could not fetch namespace {ns_id}: {e}")

    for future in as_completed(futures):
        print(future.result())

# === Files (Images, Videos, etc.) ===
# print("\n=== Downloading Files (multi-threaded) ===")
# filepages = list(site.allimages())
# 
# with ThreadPoolExecutor(max_workers=5) as executor:
#     futures = [executor.submit(download_file, fp) for fp in filepages]
#     for future in as_completed(futures):
#         print(future.result())
#         time.sleep(0.1)

print("\n✅ Mirror completed!")