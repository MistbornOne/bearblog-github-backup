#!/usr/bin/env python3
"""
Bearblog RSS Backup Script
Fetches posts from a Bearblog RSS feed and saves them as markdown files.

Usage:
  Set the BEARBLOG_RSS_URL environment variable to your Bearblog RSS feed URL.
  e.g. https://iankwatkins.com/feed/

Posts are saved to: posts/{slug}.md
"""

import html as html_lib
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import feedparser
import requests

RSS_URL = os.environ.get("BEARBLOG_RSS_URL")
OUTPUT_DIR = Path("posts")


def slugify(text: str) -> str:
    """Convert a title to a URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


def parse_date(entry) -> datetime:
    """Extract a datetime from a feed entry."""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime(*entry.published_parsed[:6])
    return datetime.utcnow()


def entry_to_markdown(entry) -> tuple[str, str]:
    """
    Convert a feed entry to (filename, markdown content).
    Returns the suggested filename and the full markdown string.
    """
    title = entry.get("title", "Untitled")
    link = entry.get("link", "")
    pub_date = parse_date(entry)
    date_str = pub_date.strftime("%Y-%m-%d")
    slug = slugify(title)
    filename = f"{slug}.md"

    # Pull summary/content — RSS usually gives us the full post body
    content = ""
    if entry.get("content"):
        content = entry.content[0].get("value", "")
    elif entry.get("summary"):
        content = entry.summary

    # --- HTML to Markdown conversion ---
    # Order matters: block-level elements must be extracted before the final
    # tag-stripping pass. Inline conversions run before blockquote/list
    # processing so inline formatting is preserved inside those elements.

    # 1. Bearblog highlighted code blocks
    #    <div class="highlight"><pre>...<button>Copy</button></pre></div>
    def convert_highlight_block(m):
        inner = m.group(1)
        inner = re.sub(r"<button[^>]*>.*?</button>", "", inner, flags=re.DOTALL)
        inner = re.sub(r"<span[^>]*>(.*?)</span>", r"\1", inner, flags=re.DOTALL)
        inner = re.sub(r"<[^>]+>", "", inner)
        return "```\n" + html_lib.unescape(inner).strip() + "\n```"

    content = re.sub(
        r'<div class="highlight"><pre>(.*?)</pre></div>',
        convert_highlight_block,
        content,
        flags=re.DOTALL,
    )

    # 2. Standard pre/code blocks (fallback)
    content = re.sub(
        r"<pre><code[^>]*>(.*?)</code></pre>",
        lambda m: "```\n" + html_lib.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() + "\n```",
        content,
        flags=re.DOTALL,
    )
    content = re.sub(
        r"<pre>(.*?)</pre>",
        lambda m: "```\n" + html_lib.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() + "\n```",
        content,
        flags=re.DOTALL,
    )

    # 3. Line breaks
    content = re.sub(r"<br\s*/?>", "\n", content)

    # 4. Paragraphs
    content = re.sub(r"<p>(.*?)</p>", r"\1\n\n", content, flags=re.DOTALL)

    # 5. Headings
    content = re.sub(
        r"<h([1-6])>(.*?)</h\1>",
        lambda m: "#" * int(m.group(1)) + " " + m.group(2) + "\n",
        content,
    )

    # 6. Images
    def convert_img(m):
        tag = m.group(0)
        src = re.search(r'src=["\']([^"\']*)["\']', tag)
        alt = re.search(r'alt=["\']([^"\']*)["\']', tag)
        return "![{}]({})".format(
            alt.group(1) if alt else "",
            src.group(1) if src else "",
        )

    content = re.sub(r"<img\b[^>]*/?>", convert_img, content)

    # 7. Links
    content = re.sub(r'<a href="(.*?)">(.*?)</a>', r"[\2](\1)", content)

    # 8. Bold / italic
    content = re.sub(r"<strong>(.*?)</strong>", r"**\1**", content)
    content = re.sub(r"<em>(.*?)</em>", r"*\1*", content)

    # 9. Blockquotes (after inline conversions so inline MD is preserved)
    def convert_blockquote(m):
        inner = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        lines = inner.splitlines()
        return "\n".join(f"> {line}" if line.strip() else ">" for line in lines) + "\n\n"

    content = re.sub(r"<blockquote>(.*?)</blockquote>", convert_blockquote, content, flags=re.DOTALL)

    # 10. Ordered lists
    def convert_ol(m):
        items = re.findall(r"<li>(.*?)</li>", m.group(1), re.DOTALL)
        lines = [f"{i + 1}. {re.sub(r'<[^>]+>', '', item).strip()}" for i, item in enumerate(items)]
        return "\n".join(lines) + "\n\n"

    content = re.sub(r"<ol>(.*?)</ol>", convert_ol, content, flags=re.DOTALL)

    # 11. Unordered lists
    def convert_ul(m):
        items = re.findall(r"<li>(.*?)</li>", m.group(1), re.DOTALL)
        lines = [f"- {re.sub(r'<[^>]+>', '', item).strip()}" for item in items]
        return "\n".join(lines) + "\n\n"

    content = re.sub(r"<ul>(.*?)</ul>", convert_ul, content, flags=re.DOTALL)

    # 12. Inline code (after block code is already handled)
    content = re.sub(r"<code>(.*?)</code>", r"`\1`", content, flags=re.DOTALL)

    # 13. Horizontal rules
    content = re.sub(r"<hr\s*/?>", "\n---\n", content)

    # 14. Strip remaining tags, then decode HTML entities
    content = re.sub(r"<[^>]+>", "", content)
    content = html_lib.unescape(content)
    content = content.strip()

    frontmatter = f"""---
title: "{title}"
date: {date_str}
source: bearblog
original_url: {link}
backed_up_at: {datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}
---

"""

    return filename, frontmatter + content


def main():
    if not RSS_URL:
        print("Error: BEARBLOG_RSS_URL environment variable is not set.")
        sys.exit(1)

    print(f"Fetching RSS feed from: {RSS_URL}")
    feed = feedparser.parse(RSS_URL)

    if feed.bozo:
        print(f"Warning: Feed parser reported an issue: {feed.bozo_exception}")

    entries = feed.entries
    if not entries:
        print("No entries found in feed.")
        return

    OUTPUT_DIR.mkdir(exist_ok=True)
    new_count = 0
    skip_count = 0

    for entry in entries:
        filename, markdown = entry_to_markdown(entry)
        output_path = OUTPUT_DIR / filename

        if output_path.exists():
            skip_count += 1
            continue

        output_path.write_text(markdown, encoding="utf-8")
        print(f"  Saved: {filename}")
        new_count += 1

    print(f"\nDone. {new_count} post(s) saved, {skip_count} unchanged.")


if __name__ == "__main__":
    main()
