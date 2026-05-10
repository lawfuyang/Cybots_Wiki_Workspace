#!/usr/bin/env python3
"""
Fetch chassis pages and extract the main image (og:image or fallback).
Adds `image1` to each entry in `chassis_data.json`.

Usage:
  python scripts/fetch_chassis_images.py [--force] [--sleep 0.8]

Requirements:
  pip install -r requirements.txt

This script is designed to be run on your machine (where internet access is available).
"""

import json
import re
import time
import argparse
import os
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


def get_og_image_from_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    meta = soup.find('meta', property='og:image')
    if meta and meta.get('content'):
        return meta.get('content')
    link = soup.find('link', rel='image_src')
    if link and link.get('href'):
        return link.get('href')
    # window.fandomContext fallback
    for script in soup.find_all('script'):
        if script.string and 'window.fandomContext' in script.string:
            m = re.search(r'window\.fandomContext\s*=\s*({.*?});', script.string, re.S)
            if m:
                try:
                    obj = json.loads(m.group(1))
                except Exception:
                    obj = None
                if obj:
                    def find_image(o):
                        if isinstance(o, dict):
                            for k, v in o.items():
                                if isinstance(v, str) and ('image' in k.lower() and v.startswith('http')):
                                    return v
                                res = find_image(v)
                                if res:
                                    return res
                        elif isinstance(o, list):
                            for i in o:
                                res = find_image(i)
                                if res:
                                    return res
                        return None
                    res = find_image(obj)
                    if res:
                        return res
    # fallback: first static.wikia image URL
    m = re.search(r'https?://static\.wikia\.nocookie\.net/[^"\s]+\.(?:jpg|jpeg|png|gif)', html, re.I)
    if m:
        return m.group(0)
    return None


def filename_from_url(u):
    """Extract the image filename from a Fandom/static.wikia URL or any image URL.
    Examples:
      https://.../images/3/34/Bulwark.jpg/revision/latest?cb=... -> Bulwark.jpg
      https://.../FileName.png -> FileName.png
    """
    if not u:
        return None
    # try regex to find the first path segment that looks like an image filename
    m = re.search(r'([^/]+\.(?:jpg|jpeg|png|gif))(?:[/?]|$)', u, re.I)
    if m:
        return m.group(1)
    # fallback: check path segments
    p = urlparse(u).path
    segs = [s for s in p.split('/') if s]
    for seg in reversed(segs):
        if re.search(r'\.(?:jpg|jpeg|png|gif)$', seg, re.I):
            return seg
    # final fallback: strip query from last segment
    last = segs[-1] if segs else ''
    last = last.split('?')[0]
    return last or None


API_URL = 'https://cybots.fandom.com/api.php'


def get_wikitext_from_api(title, headers=None):
    params = {
        'action': 'query',
        'format': 'json',
        'prop': 'revisions',
        'rvprop': 'content',
        'titles': title,
        'formatversion': 2,
    }
    try:
        r = requests.get(API_URL, params=params, headers=headers, timeout=20)
        r.raise_for_status()
        j = r.json()
        pages = j.get('query', {}).get('pages', [])
        if pages:
            revs = pages[0].get('revisions')
            if revs:
                return revs[0].get('content')
    except Exception:
        return None
    return None


def get_pageimage_from_api(title, headers=None):
    params = {
        'action': 'query',
        'format': 'json',
        'prop': 'pageimages',
        'piprop': 'original',
        'titles': title,
        'formatversion': 2,
    }
    try:
        r = requests.get(API_URL, params=params, headers=headers, timeout=20)
        r.raise_for_status()
        j = r.json()
        pages = j.get('query', {}).get('pages', [])
        if pages:
            pg = pages[0]
            orig = pg.get('original')
            if orig and orig.get('source'):
                return orig.get('source')
    except Exception:
        return None
    return None


def extract_filename_from_wikitext_value(val):
    if not val:
        return None
    v = val.strip()
    # Strip possible wikilink wrappers [[File:Name.jpg|...]] or [[Image:...]]
    m = re.search(r'\[\[\s*(?:File|Image):([^\]|\n]+)', v, re.I)
    if m:
        return m.group(1).strip()
    # If a plain filename is present
    m = re.search(r'([\w %()\-]+\.(?:jpg|jpeg|png|gif))', v, re.I)
    if m:
        return m.group(1).strip()
    # If it's a URL, extract filename
    if 'http' in v:
        return filename_from_url(v)
    # Remove any HTML tags
    v = re.sub(r'<[^>]+>', '', v)
    # Fallback: take first word
    parts = v.split('|')
    cand = parts[0].strip()
    if re.search(r'\.(?:jpg|jpeg|png|gif)$', cand, re.I):
        return cand
    return None


def extract_image_from_wikitext(wikitext):
    if not wikitext:
        return None
    # Look for |image1 = ... first
    m = re.search(r'\|\s*image1\s*=\s*([^\n\|}]*)', wikitext, re.I)
    if m:
        return extract_filename_from_wikitext_value(m.group(1))
    # Fallback to |image = ...
    m = re.search(r'\|\s*image\s*=\s*([^\n\|}]*)', wikitext, re.I)
    if m:
        return extract_filename_from_wikitext_value(m.group(1))
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--force', action='store_true', help='Refetch even if image1 already present')
    parser.add_argument('--sleep', type=float, default=0.8, help='Delay between requests in seconds')
    args = parser.parse_args()

    with open('chassis_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    headers = {'User-Agent': 'Mozilla/5.0 (compatible; cybots-image-bot/1.0)'}
    api_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://cybots.fandom.com/',
    }
    html_headers = {
        'User-Agent': api_headers['User-Agent'],
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': api_headers['Accept-Language'],
        'Referer': 'https://www.google.com/',
    }

    updated = 0

    for entry in data:
        title = entry.get('title')
        url = entry.get('url')
        if not url:
            print(f"{title}: no url, skipping")
            continue
        if not args.force and entry.get('image1'):
            print(f"{title}: already has image1, skipping")
            continue

        found = None

        # 1) Try MediaWiki API to get wikitext and extract |image1=
        try:
            wikitext = get_wikitext_from_api(title, headers=api_headers)
            if wikitext:
                fn = extract_image_from_wikitext(wikitext)
                if fn:
                    entry['image1'] = fn
                    updated += 1
                    found = fn
                    print(f"{title}: found image from wikitext {fn}")
        except Exception as e:
            print(f"{title}: wikitext API error {e}")

        # 2) Try pageimages API (original) if not found
        if not found:
            try:
                imgurl = get_pageimage_from_api(title, headers=api_headers)
                if imgurl:
                    fn = filename_from_url(imgurl)
                    if fn:
                        entry['image1'] = fn
                        updated += 1
                        found = fn
                        print(f"{title}: found image from pageimages API {fn}")
            except Exception as e:
                print(f"{title}: pageimages API error {e}")

        # 3) Fallback: fetch HTML with browser-like headers and parse
        if not found:
            try:
                r = requests.get(url, headers=html_headers, timeout=20)
                if r.status_code != 200:
                    print(f"{title}: HTTP {r.status_code}, skipping")
                else:
                    img = get_og_image_from_html(r.text)
                    if img:
                        filename = filename_from_url(img)
                        if filename:
                            entry['image1'] = filename
                            updated += 1
                            found = filename
                            print(f"{title}: found image from HTML {filename}")
                        else:
                            entry['image1'] = img
                            updated += 1
                            found = img
                            print(f"{title}: found image url but could not extract filename, saved full url")
                    else:
                        print(f"{title}: image not found in HTML")
            except Exception as e:
                print(f"{title}: HTML fetch error {e}")

        time.sleep(args.sleep)

    if updated:
        with open('chassis_data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Updated {updated} entries and wrote chassis_data.json")
    else:
        print("No updates made")


if __name__ == '__main__':
    main()
