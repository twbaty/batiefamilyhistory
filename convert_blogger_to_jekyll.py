"""
Convert Blogger Atom export to Jekyll Markdown posts.
Usage: python convert_blogger_to_jekyll.py
Output: _posts/ directory populated with YYYY-MM-DD-title.md files
"""

import xml.etree.ElementTree as ET
import os
import re
from datetime import datetime, timezone

ATOM_NS = "http://www.w3.org/2005/Atom"
BLOGGER_NS = "http://schemas.google.com/blogger/2018"
FEED_PATH = "Blogger/Blogs/Batie Family History/feed.atom"
OUTPUT_DIR = "_posts"

def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text[:60]

def parse_date(date_str):
    # Handles ISO 8601 with Z suffix
    date_str = date_str.replace("Z", "+00:00")
    return datetime.fromisoformat(date_str)

def get_text(element, tag, ns):
    el = element.find(f"{{{ns}}}{tag}")
    return el.text.strip() if el is not None and el.text else ""

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    tree = ET.parse(FEED_PATH)
    root = tree.getroot()

    entries = root.findall(f"{{{ATOM_NS}}}entry")
    posts, drafts, skipped = 0, 0, 0

    for entry in entries:
        entry_type = get_text(entry, "type", BLOGGER_NS)
        status = get_text(entry, "status", BLOGGER_NS)

        if entry_type != "POST":
            skipped += 1
            continue

        title = get_text(entry, "title", ATOM_NS) or "Untitled"
        published_str = get_text(entry, "published", ATOM_NS)
        content_el = entry.find(f"{{{ATOM_NS}}}content")
        content = content_el.text.strip() if content_el is not None and content_el.text else ""

        # Labels/tags
        tags = []
        for cat in entry.findall(f"{{{ATOM_NS}}}category"):
            term = cat.get("term", "")
            if "http://schemas.google.com/blogger" not in term and term:
                tags.append(term)

        pub_date = parse_date(published_str) if published_str else datetime.now(timezone.utc)
        date_str = pub_date.strftime("%Y-%m-%d")
        slug = slugify(title)
        filename = f"{date_str}-{slug}.md"
        filepath = os.path.join(OUTPUT_DIR, filename)

        is_draft = status == "DRAFT"
        if is_draft:
            drafts += 1
        else:
            posts += 1

        # Build YAML frontmatter
        tags_yaml = ""
        if tags:
            tags_yaml = "\ntags:\n" + "\n".join(f"  - \"{t}\"" for t in tags)

        frontmatter = f"""---
layout: post
title: "{title.replace('"', "'")}"
date: {pub_date.strftime("%Y-%m-%d %H:%M:%S %z")}{tags_yaml}
published: {"false" if is_draft else "true"}
---

"""

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(frontmatter)
            f.write(content)

        print(f"  {'[DRAFT]' if is_draft else '[POST] '} {filename}")

    print(f"\nDone: {posts} posts, {drafts} drafts, {skipped} non-posts skipped.")
    print(f"Files written to: {OUTPUT_DIR}/")

if __name__ == "__main__":
    main()
