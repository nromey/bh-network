#!/usr/bin/env python3
"""
Create news posts for CQ Blind Hams episodes using their RSS feed.

Usage:
  python3 scripts/fetch_cqbh.py [--feed URL] [--output DIR]
                                [--limit N | --all] [--since YYYY-MM-DD]
                                [--dry-run]

Defaults:
  --feed   https://anchor.fm/s/123c50ac/podcast/rss
  --output _posts
  --limit  1 (unless --all is set)

Behavior:
  - Reads the RSS feed and sorts items by pubDate (newest first).
  - Selects up to N most-recent items, or all with --all.
  - Optionally filters to items on/after --since (YYYY-MM-DD).
  - For each unseen episode (based on GUID/title), writes a Jekyll post
    whose filename date and front matter date match the RSS pubDate.
  - Embeds an Able Player with the MP3 enclosure.

This script uses only the Python standard library for portability.
"""

from __future__ import annotations

import argparse
import html
import os
import re
import sys
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path
from string import Template


DEFAULT_FEED = "https://anchor.fm/s/123c50ac/podcast/rss"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "bhn-fetch-cqbh/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read()


def text_of(elem: ET.Element | None) -> str:
    if elem is None:
        return ""
    # Prefer CDATA if present; ET preserves it as text
    return (elem.text or "").strip()


def make_slug(title: str) -> str:
    base = title.lower().strip()
    # Replace em/en dashes with hyphen
    base = base.replace("—", "-").replace("–", "-")
    # Replace non-word with hyphen, collapse repeats
    base = re.sub(r"[^a-z0-9]+", "-", base)
    base = re.sub(r"-+", "-", base).strip("-")
    return base[:80] or "episode"


def extract_items(feed_xml: bytes):
    ns = {
        "content": "http://purl.org/rss/1.0/modules/content/",
        "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
    }
    root = ET.fromstring(feed_xml)
    channel = root.find("channel")
    if channel is None:
        return []
    items = []
    for item in channel.findall("item"):
        title = text_of(item.find("title"))
        desc_html = text_of(item.find("{http://purl.org/rss/1.0/modules/content/}encoded")) or text_of(item.find("description"))
        pub_str = text_of(item.find("pubDate"))
        guid = text_of(item.find("guid")) or text_of(item.find("link"))
        enc = item.find("enclosure")
        mp3_url = enc.get("url") if enc is not None else None
        try:
            pub_dt = parsedate_to_datetime(pub_str) if pub_str else None
        except Exception:
            pub_dt = None
        items.append({
            "title": title,
            "desc_html": desc_html,
            "pub_dt": pub_dt,
            "guid": guid,
            "mp3_url": mp3_url,
        })
    # Sort descending by pub date if available
    items.sort(key=lambda x: x["pub_dt"] or parsedate_to_datetime("Mon, 01 Jan 1990 00:00:00 GMT"), reverse=True)
    return items


POST_TEMPLATE = Template("""---
layout: post
title: "$title"
date: $date_iso
categories: [news, cqbh]
tags: [podcast, CQ Blind Hams]
ableplayer: true
cqbh_guid: $guid
---

$intro

{% include able_audio.html title="$player_title" src="$mp3_url" fallback_url="$mp3_url" %}

Description (from CQ Blind Hams):

$desc_html
""")


def write_post(item: dict, out_dir: Path, dry_run: bool = False) -> Path | None:
    title = item["title"].strip() or "CQ Blind Hams — New Episode"
    # Ensure a consistent title prefix for our site
    site_title = title
    if not title.lower().startswith("new cq blind hams podcast"):
        # Example: "New CQ Blind Hams Podcast: {title}"
        site_title = f"New CQ Blind Hams Podcast: {title}"

    pub_dt = item["pub_dt"]
    if pub_dt is None:
        # Fallback to current time if date missing
        from datetime import datetime, timezone
        pub_dt = datetime.now(timezone.utc)

    date_part = pub_dt.strftime("%Y-%m-%d")
    # Normalize to local-naive time if tzinfo missing; keep ISO for clarity
    date_iso = pub_dt.strftime("%Y-%m-%d %H:%M:%S %z") or f"{date_part} 00:00:00 +0000"

    slug = make_slug(title)
    filename = f"{date_part}-{slug}.md"
    path = out_dir / filename

    # Skip if a post with this guid already exists
    guid = (item["guid"] or item["mp3_url"] or slug).strip()
    # Quick scan for existing guid in posts
    for p in sorted(out_dir.glob("*.md")):
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if f"cqbh_guid: {guid}" in txt or f"title: \"{title}\"" in txt:
            return None

    mp3_url = item["mp3_url"]
    if not mp3_url:
        # Without audio there is no player; still post a link if available
        mp3_url = ""

    intro = (
        "A new episode of the CQ Blind Hams podcast is out: \"%s\". "
        "You can listen on Apple Podcasts, Spotify, and YouTube; "
        "we’ve embedded the episode below for easy playback."
    ) % (html.escape(title),)
    player_title = html.escape(title)
    desc_html = item["desc_html"].strip() or ""
    # Keep HTML as-is; Template handles braces fine

    content = POST_TEMPLATE.safe_substitute(
        title=site_title,
        date_iso=date_iso,
        guid=guid,
        intro=intro,
        player_title=player_title,
        mp3_url=mp3_url,
        desc_html=desc_html,
    )

    if dry_run:
        print(f"[DRY-RUN] Would write: {path}")
        print(content)
        return None

    path.write_text(content, encoding="utf-8")
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--feed", default=DEFAULT_FEED)
    ap.add_argument("--output", default="_posts")
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--limit", type=int, default=1, help="number of newest episodes to post")
    group.add_argument("--all", action="store_true", help="create posts for all episodes in the feed")
    ap.add_argument("--since", help="only include episodes on/after this date (YYYY-MM-DD)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        data = fetch(args.feed)
    except urllib.error.URLError as e:
        print(f"Error: failed to fetch feed: {e}", file=sys.stderr)
        return 2

    items = extract_items(data)

    # Optional date filter
    if args.since:
        try:
            from datetime import datetime
            since_dt = datetime.strptime(args.since, "%Y-%m-%d")
        except Exception:
            print("Error: --since must be YYYY-MM-DD", file=sys.stderr)
            return 2
        items = [it for it in items if it["pub_dt"] and it["pub_dt"].date().isoformat() >= args.since]

    # Selection: all or limit N
    selected = items if args.all else items[: max(1, args.limit) ]

    created = []
    for item in selected:
        path = write_post(item, out_dir, dry_run=args.dry_run)
        if path:
            created.append(path)

    if created:
        for p in created:
            print(f"Created: {p}")
        return 0
    else:
        print("No new posts created (already up to date).")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
