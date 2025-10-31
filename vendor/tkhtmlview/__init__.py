"""A lightweight HTML display widget built on top of ``tkinter``.

The implementation mirrors the subset of the ``tkhtmlview`` API that the
assistant relies on (currently only :class:`HTMLScrolledText` with a
``set_html`` method).
"""
from __future__ import annotations

import tkinter as tk
from tkinter import scrolledtext
from tkinter import font as tkfont
from html.parser import HTMLParser
import webbrowser
from typing import Callable, List, Optional

__all__ = ["HTMLScrolledText"]


class _HTMLRenderer(HTMLParser):
    """Render a restricted HTML subset into a ``tk.Text`` widget."""

    def __init__(
            self,
            widget: tk.Text,
            register_link: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        super().__init__(convert_charrefs=True)
        self.widget = widget
        self._register_link = register_link
        self.inline_tags: List[str] = []
        self.list_stack: List[dict[str, int]] = []
        self._pending_newlines = 0
        self._text_written = False
        self._link_stack: List[str] = []
        self._link_counter = 0

    # -- Helpers ---------------------------------------------------------
    def _queue_newlines(self, count: int) -> None:
        if self._text_written:
            self._pending_newlines = max(self._pending_newlines, count)
            # self._pending_newlines = 1 if count == 1 else max(self._pending_newlines, count)

    def _flush_newlines(self) -> None:
        if self._pending_newlines:
            self.widget.insert(tk.END, "\n" * self._pending_newlines)
            self._pending_newlines = 0
            self._text_written = True

    def _pop_inline_tag(self, name: str) -> None:
        for index in range(len(self.inline_tags) - 1, -1, -1):
            if self.inline_tags[index] == name:
                self.inline_tags.pop(index)
                break

    # -- HTMLParser API --------------------------------------------------
    def handle_starttag(self, tag: str, attrs: List[tuple[str, str | None]]) -> None:
        # if tag in {"p", "div"}:
        #    self._queue_newlines(1)
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.inline_tags.append(tag)
        elif tag == "br":
            self._queue_newlines(1)
            self._flush_newlines()
        elif tag == "ul":
        #    self._queue_newlines(1)
            self.list_stack.append({"type": "ul", "index": 0})
        elif tag == "ol":
        #    self._queue_newlines(1)
            self.list_stack.append({"type": "ol", "index": 0})
        elif tag == "li":
            # self._queue_newlines(1)
            self._flush_newlines()
            bullet = "• "
            if self.list_stack:
                current = self.list_stack[-1]
                if current["type"] == "ol":
                    current["index"] += 1
                    bullet = f"{current['index']}. "
            self.widget.insert(tk.END, bullet)
            self._text_written = True
        elif tag in {"strong", "b"}:
            self.inline_tags.append("bold")
        elif tag in {"em", "i"}:
            self.inline_tags.append("italic")
        elif tag == "code":
            self.inline_tags.append("code")
        elif tag == "a":
            href: Optional[str] = None
            for attr_name, attr_value in attrs:
                if attr_name.lower() == "href" and attr_value:
                    href = attr_value
                    break
            link_tag = "link"
            if href and self._register_link is not None:
                self._link_counter += 1
                link_tag = f"link_{self._link_counter}"
                try:
                    self._register_link(link_tag, href)
                except Exception:
                    link_tag = "link"
            self.inline_tags.append(link_tag)
            self._link_stack.append(link_tag)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"p"}:
            self._queue_newlines(1)
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._pop_inline_tag(tag)
            self._queue_newlines(1)
        # elif tag == "li":
        #    self._queue_newlines(1)
        elif tag == "ul":
            if self.list_stack:
                self.list_stack.pop()
        #    self._queue_newlines(1)
        elif tag == "ol":
            if self.list_stack:
                self.list_stack.pop()
        #    self._queue_newlines(1)
        elif tag in {"strong", "b"}:
            self._pop_inline_tag("bold")
        elif tag in {"em", "i"}:
            self._pop_inline_tag("italic")
        elif tag == "code":
            self._pop_inline_tag("code")
        elif tag == "a":
            link_tag = self._link_stack.pop() if self._link_stack else None
            if link_tag:
                self._pop_inline_tag(link_tag)

    def handle_startendtag(self, tag: str, attrs: List[tuple[str, str | None]]) -> None:
        if tag == "br":
            self._queue_newlines(1)
            self._flush_newlines()

    def handle_data(self, data: str) -> None:
        if not data:
            return
        self._flush_newlines()
        tags = tuple(self.inline_tags)
        if tags:
            self.widget.insert(tk.END, data, tags)
        else:
            self.widget.insert(tk.END, data)
        self._text_written = True

    def close(self) -> None:  # type: ignore[override]
        super().close()
        self._flush_newlines()


class HTMLScrolledText(scrolledtext.ScrolledText):
    """A ``ScrolledText`` widget that understands a subset of HTML."""

    def __init__(self, master: tk.Misc | None = None, **kwargs) -> None:
        kwargs.setdefault("wrap", tk.WORD)
        super().__init__(master, **kwargs)
        self.raw_markdown = ""
        self._link_tags: dict[str, str] = {}
        self._configure_tags()

    # -- Tag configuration ------------------------------------------------
    def _configure_tags(self) -> None:
        base_font = tkfont.nametofont(self.cget("font")).copy()

        bold_font = base_font.copy()
        bold_font.configure(weight="bold")
        self.tag_configure("bold", font=bold_font)

        italic_font = base_font.copy()
        italic_font.configure(slant="italic")
        self.tag_configure("italic", font=italic_font)

        code_font = base_font.copy()
        code_font.configure(family="Courier", size=max(base_font["size"] - 1, 8))
        self.tag_configure("code", font=code_font)

        for level in range(1, 7):
            heading_font = base_font.copy()
            heading_font.configure(weight="bold", size=max(base_font["size"] + 6 - (level * 2), base_font["size"]))
            self.tag_configure(f"h{level}", font=heading_font, spacing1=4, spacing3=4)

        self.tag_configure("link", foreground="#0645AD", underline=True)
        self.tag_bind("link", "<Button-1>", self._open_default_link)
        self.tag_bind("link", "<Enter>", lambda _event: self.config(cursor="hand2"))
        self.tag_bind("link", "<Leave>", lambda _event: self.config(cursor=""))

    # -- Public API ------------------------------------------------------
    def set_html(self, html_content: str) -> None:
        """Render the supplied HTML string inside the widget."""

        self.config(state=tk.NORMAL)
        self.delete("1.0", tk.END)
        self._clear_dynamic_links()
        renderer = _HTMLRenderer(self, self._register_link_tag)
        renderer.feed(html_content or "")
        renderer.close()
        self.see("1.0")

    def clear(self) -> None:
        """Convenience method to empty the widget."""

        self.config(state=tk.NORMAL)
        self.delete("1.0", tk.END)
        self.raw_markdown = ""

# -- Internal helpers ------------------------------------------------
    def _register_link_tag(self, tag_name: str, href: str) -> None:
        self._link_tags[tag_name] = href
        self.tag_configure(tag_name, foreground="#0645AD", underline=True)
        self.tag_bind(tag_name, "<Button-1>", lambda _event, url=href: self._open_link(url))
        self.tag_bind(tag_name, "<Enter>", lambda _event: self.config(cursor="hand2"))
        self.tag_bind(tag_name, "<Leave>", lambda _event: self.config(cursor=""))

    def _clear_dynamic_links(self) -> None:
        for tag in list(self._link_tags):
            self.tag_unbind(tag, "<Button-1>")
            self.tag_unbind(tag, "<Enter>")
            self.tag_unbind(tag, "<Leave>")
            self.tag_delete(tag)
            self._link_tags.pop(tag, None)
        self.config(cursor="")

    def _open_link(self, url: str) -> None:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    def _open_default_link(self, _event: tk.Event) -> None:
        url = self._link_tags.get("link")
        if url:
            self._open_link(url)