"""A very small Markdown to HTML renderer for offline environments.

The implementation supports the subset of Markdown required by the assistant
(headings, paragraphs, emphasis, inline code and unordered/ordered lists).
It mirrors the ``markdown`` package's ``markdown`` function so that the rest
of the application can treat it as a drop-in replacement.
"""
from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from typing import List

__all__ = ["markdown", "to_plain_text"]

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_BULLET_RE = re.compile(r"^[-*]\s+(.*)$")
_ORDERED_RE = re.compile(r"^(\d+)[\.)]\s+(.*)$")


def _apply_inline_markup(text: str) -> str:
    """Apply inline Markdown transformations to *text* and return HTML."""

    escaped = html.escape(text, quote=False)

    def replace(pattern: str, repl: str, value: str) -> str:
        return re.sub(pattern, repl, value, flags=re.MULTILINE)

    # Bold (**text** or __text__)
    escaped = replace(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = replace(r"__(.+?)__", r"<strong>\1</strong>", escaped)
    # Italic (*text* or _text_). Tempered patterns avoid swallowing the bold
    # markers themselves.
    escaped = replace(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", escaped)
    escaped = replace(r"(?<!_)_(?!_)(.+?)(?<!_)_(?!_)", r"<em>\1</em>", escaped)
    # Inline code (`code`).
    escaped = replace(r"`(.+?)`", lambda match: f"<code>{match.group(1)}</code>", escaped)
    return escaped


def markdown(text: str) -> str:
    """Convert Markdown *text* into HTML.

    Only a limited subset of Markdown is supported. The function focuses on
    clarity and predictable output for the UI rather than strict Markdown
    compliance.
    """

    lines = text.splitlines()
    blocks: List[str] = []
    paragraph_lines: List[str] = []
    list_type: str | None = None

    def flush_paragraph() -> None:
        nonlocal paragraph_lines
        if not paragraph_lines:
            return
        paragraph_raw = "\n".join(paragraph_lines)
        paragraph_html = _apply_inline_markup(paragraph_raw).replace("\n", "<br />")
        blocks.append(f"<p>{paragraph_html}</p>")
        paragraph_lines = []

    def close_list() -> None:
        nonlocal list_type
        if list_type:
            blocks.append(f"</{list_type}>")
            list_type = None

    for raw_line in lines:
        stripped = raw_line.strip()
        if not stripped:
            flush_paragraph()
            close_list()
            continue

        heading_match = _HEADING_RE.match(stripped)
        if heading_match:
            flush_paragraph()
            close_list()
            level = len(heading_match.group(1))
            content = _apply_inline_markup(heading_match.group(2).strip())
            blocks.append(f"<h{level}>{content}</h{level}>")
            continue

        bullet_match = _BULLET_RE.match(stripped)
        if bullet_match:
            flush_paragraph()
            if list_type not in {"ul"}:
                close_list()
                list_type = "ul"
                blocks.append("<ul>")
            content = _apply_inline_markup(bullet_match.group(1).strip())
            blocks.append(f"<li>{content}</li>")
            continue

        ordered_match = _ORDERED_RE.match(stripped)
        if ordered_match:
            flush_paragraph()
            if list_type not in {"ol"}:
                close_list()
                list_type = "ol"
                blocks.append("<ol>")
            content = _apply_inline_markup(ordered_match.group(2).strip())
            blocks.append(f"<li>{content}</li>")
            continue

        close_list()
        paragraph_lines.append(stripped)

    flush_paragraph()
    close_list()

    return "\n".join(blocks)


class _PlainTextExtractor(HTMLParser):
    """Convert the HTML produced by :func:`markdown` into plain text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: List[str] = []
        self._list_stack: List[dict[str, int]] = []

    # -- Helpers ---------------------------------------------------------
    def _append_newline(self, count: int = 1) -> None:
        if not self._parts:
            return
        # Prevent runaway blank lines by ensuring at most two consecutive ones.
        trailing = 0
        for chunk in reversed(self._parts):
            if not chunk:
                continue
            if chunk.endswith("\n"):
                trailing += len(chunk) - len(chunk.rstrip("\n"))
                if trailing >= count:
                    break
            else:
                break
        missing = count - trailing
        if missing > 0:
            self._parts.append("\n" * missing)

    # -- HTMLParser API --------------------------------------------------
    def handle_starttag(self, tag: str, attrs: List[tuple[str, str | None]]) -> None:
        if tag in {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self._append_newline()
        elif tag == "br":
            self._parts.append("\n")
        elif tag == "ul":
            self._list_stack.append({"type": "ul", "index": 0})
        elif tag == "ol":
            self._list_stack.append({"type": "ol", "index": 0})
        elif tag == "li":
            self._append_newline()
            if self._list_stack:
                current = self._list_stack[-1]
                if current["type"] == "ul":
                    self._parts.append("- ")
                else:
                    current["index"] += 1
                    self._parts.append(f"{current['index']}. ")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"p", "div"}:
            self._append_newline(2)
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._append_newline(2)
        elif tag == "li":
            self._append_newline()
        elif tag in {"ul", "ol"}:
            if self._list_stack:
                self._list_stack.pop()
            self._append_newline(2)

    def handle_data(self, data: str) -> None:
        if data and not data.isspace():
            self._parts.append(data)

    # -- Public API ------------------------------------------------------
    def get_text(self) -> str:
        joined = "".join(self._parts)
        lines = [line.rstrip() for line in joined.splitlines()]
        cleaned: List[str] = []
        previous_blank = True
        for line in lines:
            if line:
                cleaned.append(line)
                previous_blank = False
            else:
                if not previous_blank:
                    cleaned.append("")
                previous_blank = True
        while cleaned and not cleaned[-1]:
            cleaned.pop()
        return "\n".join(cleaned)


def to_plain_text(text: str) -> str:
    """Return a plain-text representation of the supplied Markdown string."""

    extractor = _PlainTextExtractor()
    extractor.feed(markdown(text))
    extractor.close()
    return extractor.get_text()
