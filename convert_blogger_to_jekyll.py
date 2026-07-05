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

def clean_html(body):
    # Strip Blogger data attributes
    body = re.sub(r'\s+data-path-to-node="[^"]*"', "", body)
    body = re.sub(r'\s+data-index-in-node="[^"]*"', "", body)
    body = re.sub(r'\s+data-original-height="[^"]*"', "", body)
    body = re.sub(r'\s+data-original-width="[^"]*"', "", body)
    body = re.sub(r'\s+border="0"', "", body)

    # Wrap separator divs (image containers) in a centered post-image div,
    # preserving the <a href><img></a> click-to-enlarge link
    def wrap_separator(m):
        inner = m.group(1).strip()
        # Add target="_blank" to image links so they open in a new tab
        inner = re.sub(r'<a ', '<a target="_blank" ', inner)
        if not inner:
            return ""
        return f'\n<div class="post-image">{inner}</div>\n'

    body = re.sub(r'<div class="separator"[^>]*>(.*?)</div>',
                  wrap_separator, body, flags=re.DOTALL)

    # Remove empty paragraphs and stray &nbsp;
    body = re.sub(r'<p>\s*(&nbsp;)?\s*</p>', '', body)
    body = re.sub(r'<br\s*/?>(\s*&nbsp;)+', '', body)
    body = re.sub(r'<br\s*/?>', '\n', body)

    # Add newlines around block elements so Kramdown parses HTML correctly
    block_open  = r'(<(?:p|h[1-6]|div|ul|ol|li|blockquote|pre|hr)\b[^>]*>)'
    block_close = r'(</(?:p|h[1-6]|div|ul|ol|li|blockquote|pre)>)'
    body = re.sub(block_open,  r'\n\1', body)
    body = re.sub(block_close, r'\1\n', body)

    # Collapse extra blank lines
    body = re.sub(r'\n{3,}', '\n\n', body).strip()
    return body


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

        content = clean_html(content)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(frontmatter)
            f.write(content)

        print(f"  {'[DRAFT]' if is_draft else '[POST] '} {filename}")

    print(f"\nDone: {posts} posts, {drafts} drafts, {skipped} non-posts skipped.")
    print(f"Files written to: {OUTPUT_DIR}/")

if __name__ == "__main__":
    main()
