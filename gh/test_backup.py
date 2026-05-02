"""Tests for gh/backup.py"""

import re
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import backup


# ---------------------------------------------------------------------------
# Feedparser-style entry helper
# feedparser entries support both dict-style .get() AND attribute access.
# ---------------------------------------------------------------------------

class FeedEntry(dict):
    """Dict subclass that also allows attribute access, mirroring feedparser."""
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)


def make_entry(title="Test Post", link="https://example.com/test",
               published_parsed=(2024, 1, 10, 0, 0, 0, 0, 0, 0),
               summary=None, content=None):
    e = FeedEntry(title=title, link=link, published_parsed=published_parsed)
    if summary is not None:
        e["summary"] = summary
    if content is not None:
        e["content"] = content
    return e


# ---------------------------------------------------------------------------
# slugify
# ---------------------------------------------------------------------------

class TestSlugify:
    def test_basic(self):
        assert backup.slugify("Hello World") == "hello-world"

    def test_special_chars_stripped(self):
        assert backup.slugify("It's a test!") == "its-a-test"

    def test_multiple_spaces_and_hyphens(self):
        assert backup.slugify("foo  --  bar") == "foo-bar"

    def test_leading_trailing_hyphens(self):
        assert backup.slugify("  -hello-  ") == "hello"

    def test_empty_string(self):
        assert backup.slugify("") == ""


# ---------------------------------------------------------------------------
# parse_date
# ---------------------------------------------------------------------------

class TestParseDate:
    def test_uses_published_parsed(self):
        entry = FeedEntry(published_parsed=(2024, 3, 15, 10, 0, 0, 0, 0, 0))
        result = backup.parse_date(entry)
        assert result == datetime(2024, 3, 15, 10, 0, 0)

    def test_falls_back_to_utcnow_when_none(self):
        entry = FeedEntry(published_parsed=None)
        before = datetime.utcnow()
        result = backup.parse_date(entry)
        after = datetime.utcnow()
        assert before <= result <= after

    def test_falls_back_when_no_attribute(self):
        entry = FeedEntry()  # no published_parsed key at all
        before = datetime.utcnow()
        result = backup.parse_date(entry)
        after = datetime.utcnow()
        assert before <= result <= after


# ---------------------------------------------------------------------------
# entry_to_markdown
# ---------------------------------------------------------------------------

class TestEntryToMarkdown:
    def test_filename_format(self):
        filename, _ = backup.entry_to_markdown(make_entry())
        assert filename == "test-post.md"

    def test_frontmatter_fields(self):
        _, md = backup.entry_to_markdown(make_entry())
        assert 'title: "Test Post"' in md
        assert "date: 2024-01-10" in md
        assert "source: bearblog" in md
        assert "original_url: https://example.com/test" in md
        assert "backed_up_at:" in md

    def test_html_stripped_from_summary(self):
        entry = make_entry(summary="<p>Hello <strong>world</strong></p>")
        _, md = backup.entry_to_markdown(entry)
        assert "<p>" not in md
        assert "<strong>" not in md
        assert "Hello" in md
        assert "**world**" in md

    def test_content_preferred_over_summary(self):
        content_list = [FeedEntry(value="<p>Content text</p>")]
        entry = make_entry(summary="summary text", content=content_list)
        _, md = backup.entry_to_markdown(entry)
        assert "Content text" in md
        assert "summary text" not in md

    def test_br_tags_become_newlines(self):
        entry = make_entry(summary="line1<br/>line2")
        _, md = backup.entry_to_markdown(entry)
        assert "line1\nline2" in md

    def test_anchor_tags_converted(self):
        entry = make_entry(summary='<a href="https://x.com">click</a>')
        _, md = backup.entry_to_markdown(entry)
        assert "[click](https://x.com)" in md

    def test_headings_converted(self):
        entry = make_entry(summary="<h2>Section</h2>")
        _, md = backup.entry_to_markdown(entry)
        assert "## Section" in md

    def test_missing_title_defaults(self):
        entry = FeedEntry()
        filename, md = backup.entry_to_markdown(entry)
        assert "untitled" in filename
        assert 'title: "Untitled"' in md

    # --- New conversion tests ---

    def test_highlighted_code_block(self):
        html = (
            '<div class="highlight"><pre>'
            '<span></span>'
            '<span class="k">def</span>'
            '<span class="w"> </span>'
            '<span class="nf">f</span>'
            '<span class="p">():</span>\n'
            '    pass\n'
            '<button class="copy-code-button" type="button">Copy</button>'
            '</pre></div>'
        )
        entry = make_entry(summary=html)
        _, md = backup.entry_to_markdown(entry)
        assert "```" in md
        assert "def f():" in md
        assert "pass" in md
        assert "Copy" not in md
        assert "<span" not in md

    def test_blockquote_converted(self):
        entry = make_entry(summary="<blockquote>great quote</blockquote>")
        _, md = backup.entry_to_markdown(entry)
        assert "> great quote" in md

    def test_image_converted(self):
        entry = make_entry(summary='<img src="https://x.com/img.png" alt="a cat">')
        _, md = backup.entry_to_markdown(entry)
        assert "![a cat](https://x.com/img.png)" in md

    def test_image_alt_before_src(self):
        entry = make_entry(summary='<img alt="a cat" src="https://x.com/img.png"/>')
        _, md = backup.entry_to_markdown(entry)
        assert "![a cat](https://x.com/img.png)" in md

    def test_unordered_list_converted(self):
        entry = make_entry(summary="<ul><li>alpha</li><li>beta</li></ul>")
        _, md = backup.entry_to_markdown(entry)
        assert "- alpha" in md
        assert "- beta" in md

    def test_ordered_list_converted(self):
        entry = make_entry(summary="<ol><li>first</li><li>second</li></ol>")
        _, md = backup.entry_to_markdown(entry)
        assert "1. first" in md
        assert "2. second" in md

    def test_inline_code_converted(self):
        entry = make_entry(summary="use <code>print()</code> here")
        _, md = backup.entry_to_markdown(entry)
        assert "`print()`" in md

    def test_html_entities_unescaped(self):
        entry = make_entry(summary="a &amp; b &lt;3")
        _, md = backup.entry_to_markdown(entry)
        assert "a & b <3" in md


# ---------------------------------------------------------------------------
# OUTPUT_DIR points to posts/
# ---------------------------------------------------------------------------

def test_output_dir_is_posts():
    assert backup.OUTPUT_DIR == Path("posts")


# ---------------------------------------------------------------------------
# main() — integration-style with mocked feedparser and filesystem
# ---------------------------------------------------------------------------

def _make_feed(entries):
    feed = MagicMock()
    feed.bozo = False
    feed.entries = entries
    return feed


class TestMain:
    def test_saves_new_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(backup, "OUTPUT_DIR", tmp_path)
        monkeypatch.setattr(backup, "RSS_URL", "https://fake.rss")

        entry = make_entry(summary="Body text")
        with patch("backup.feedparser.parse", return_value=_make_feed([entry])):
            backup.main()

        files = list(tmp_path.glob("*.md"))
        assert len(files) == 1
        assert "test-post" in files[0].name

    def test_skips_unchanged_file(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(backup, "OUTPUT_DIR", tmp_path)
        monkeypatch.setattr(backup, "RSS_URL", "https://fake.rss")

        entry = make_entry(summary="Body text")
        with patch("backup.feedparser.parse", return_value=_make_feed([entry])):
            backup.main()  # first run — creates file
            backup.main()  # second run — should skip

        captured = capsys.readouterr()
        assert "1 unchanged" in captured.out

    def test_exits_without_rss_url(self, monkeypatch):
        monkeypatch.setattr(backup, "RSS_URL", None)
        with pytest.raises(SystemExit):
            backup.main()

    def test_no_entries_exits_cleanly(self, tmp_path, monkeypatch):
        monkeypatch.setattr(backup, "OUTPUT_DIR", tmp_path)
        monkeypatch.setattr(backup, "RSS_URL", "https://fake.rss")

        with patch("backup.feedparser.parse", return_value=_make_feed([])):
            backup.main()

        assert list(tmp_path.glob("*.md")) == []
