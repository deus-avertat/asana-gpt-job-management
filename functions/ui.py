from __future__ import annotations

import sys
import tkinter as tk
from tkinter import messagebox

from typing import Any, Callable

from docx import Document

import PyPDF2

from vendor_setup import ensure_vendor_path

ensure_vendor_path()

import markdown

from functions.clipboard import get_clipboard_html, set_clipboard_html


CF_HTML_HEADER_TEMPLATE = (
    "Version:0.9\r\n"
    "StartHTML:{start_html:010d}\r\n"
    "EndHTML:{end_html:010d}\r\n"
    "StartFragment:{start_fragment:010d}\r\n"
    "EndFragment:{end_fragment:010d}\r\n"
    "SourceURL:{source_url}\r\n"
    "\r\n"
)


def _build_cf_html(html_fragment: str, *, source_url: str = "") -> str:
    """Return an HTML clipboard payload that complies with the CF_HTML spec."""

    if not html_fragment:
        html_fragment = ""

    if "<html" in html_fragment.lower():
        body = html_fragment
    else:
        body = f"<html><body>{html_fragment}</body></html>"

    if "<!--StartFragment-->" not in body:
        replaced = body.replace("<body>", "<body><!--StartFragment-->", 1)
        if replaced == body:
            replaced = "<!--StartFragment-->" + replaced
        body = replaced.replace("</body>", "<!--EndFragment--></body>", 1)
        if "<!--EndFragment-->" not in body:
            body = body + "<!--EndFragment-->"

    placeholder_header = CF_HTML_HEADER_TEMPLATE.format(
        start_html=0,
        end_html=0,
        start_fragment=0,
        end_fragment=0,
        source_url=source_url,
    )

    header_bytes = placeholder_header.encode("utf-8")
    body_bytes = body.encode("utf-8")

    start_html = len(header_bytes)
    start_fragment_marker = body_bytes.find(b"<!--StartFragment-->")
    end_fragment_marker = body_bytes.find(b"<!--EndFragment-->")

    if start_fragment_marker == -1 or end_fragment_marker == -1:
        # Should not happen due to guards above, but fall back gracefully.
        start_fragment_marker = 0
        end_fragment_marker = len(body_bytes)

    start_fragment = start_html + start_fragment_marker + len(b"<!--StartFragment-->")
    end_fragment = start_html + end_fragment_marker
    end_html = start_html + len(body_bytes)

    header = CF_HTML_HEADER_TEMPLATE.format(
        start_html=start_html,
        end_html=end_html,
        start_fragment=start_fragment,
        end_fragment=end_fragment,
        source_url=source_url,
    )

    return header + body


def _is_list_item(line: str) -> bool:
    """Return ``True`` when *line* represents a Markdown list item."""

    stripped = line.lstrip()
    if not stripped:
        return False
    if stripped[0] in "-*+" and (len(stripped) == 1 or stripped[1].isspace()):
        return True
    if stripped[0].isdigit():
        index = 0
        length = len(stripped)
        while index < length and stripped[index].isdigit():
            index += 1
        if index and index < length and stripped[index] in {".", ")"}:
            index += 1
            if index == length or stripped[index].isspace():
                return True
    return False


def normalize_markdown_spacing(markdown_text: str) -> str:
    """Condense excessive blank lines while keeping Markdown structure."""

    if not markdown_text:
        return ""

    # print(markdown_text) # For debugging output

    lines = markdown_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    normalized: list[str] = []
    blank_run = 0
    last_nonempty: str | None = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            blank_run += 1
            continue

        is_list_item = _is_list_item(line)
        if blank_run:
            if not (is_list_item and last_nonempty is not None and _is_list_item(last_nonempty)):
                normalized.append("")
        normalized.append(line.rstrip())
        blank_run = 0
        last_nonempty = line

    return "\n".join(normalized).strip()


def get_date(cal_var):
    selected_date = cal_var.get()
    print(f"INFO: Selected Date: {selected_date}")
    return selected_date

def copy_output(tk_root, output_text, *, show_alert: bool = True):
    print("INFO: Copied Output to Clipboard")
    markdown_text = get_widget_markdown(output_text)
    html_text = getattr(output_text, "rendered_html", None)
    if not html_text:
        html_text = markdown.markdown(markdown_text)

    cf_html = _build_cf_html(html_text)

    plain_text = markdown_to_plain_text(markdown_text) if markdown_text else ""

    success = set_clipboard_html(tk_root, plain_text, html_text, cf_html)

    if not success:
        try:
            tk_root.clipboard_clear()
            fallback_text = plain_text or markdown_text or html_text
            if fallback_text:
                tk_root.clipboard_append(fallback_text)
                success = True
        except tk.TclError:
            success = False
    if show_alert:
        messagebox.showinfo("Copied", "Output copied to clipboard.")


def _bind_sequence(widget: tk.Misc, sequence: str, callback: Callable[[tk.Event], str | None]) -> None:
    """Safely attach *callback* to *sequence* without clobbering defaults."""

    try:
        widget.bind(sequence, callback, add=True)
    except TypeError:  # pragma: no cover - Tk < 8.6 compatibility
        widget.bind(sequence, callback)


def enable_html_clipboard_paste(widget: tk.Text) -> None:
    """Allow ``widget`` to render HTML fragments when pasted from the clipboard."""

    def _handle_paste(event: tk.Event) -> str | None:
        html_fragment = get_clipboard_html(widget)
        if not html_fragment:
            return None

        if hasattr(widget, "set_html"):
            try:
                widget.set_html(html_fragment)
            except Exception:  # pragma: no cover - defensive fallback
                widget.delete("1.0", tk.END)
                widget.insert(tk.INSERT, html_fragment)
        else:  # pragma: no cover - compatibility fallback
            widget.delete("1.0", tk.END)
            widget.insert(tk.INSERT, html_fragment)

        setattr(widget, "raw_html", html_fragment)
        return "break"

    _bind_sequence(widget, "<<Paste>>", _handle_paste)
    _bind_sequence(widget, "<Control-v>", _handle_paste)
    _bind_sequence(widget, "<Control-V>", _handle_paste)
    _bind_sequence(widget, "<Shift-Insert>", _handle_paste)
    if sys.platform == "darwin":  # pragma: no cover - macOS specific shortcut
        _bind_sequence(widget, "<Command-v>", _handle_paste)
        _bind_sequence(widget, "<Command-V>", _handle_paste)

def enable_html_clipboard_copy(tk_root: tk.Misc, widget: tk.Text) -> None:
    """Ensure ``widget`` advertises HTML when copied via keyboard shortcuts."""

    def _handle_copy(event: tk.Event) -> str | None:
        copy_output(tk_root, widget, show_alert=False)
        return "break"

    _bind_sequence(widget, "<<Copy>>", _handle_copy)
    _bind_sequence(widget, "<Control-c>", _handle_copy)
    _bind_sequence(widget, "<Control-C>", _handle_copy)
    _bind_sequence(widget, "<Control-Insert>", _handle_copy)
    if sys.platform == "darwin":  # pragma: no cover - macOS shortcut
        _bind_sequence(widget, "<Command-c>", _handle_copy)
        _bind_sequence(widget, "<Command-C>", _handle_copy)

def get_widget_markdown(output_widget: Any) -> str:
    """Return the raw Markdown stored on an output widget."""

    raw_value = getattr(output_widget, "raw_markdown", None)
    if isinstance(raw_value, str):
        return raw_value.strip()
    try:
        return output_widget.get("1.0", tk.END).strip()
    except Exception:  # pragma: no cover - fallback for unexpected widgets
        return ""


def display_markdown(output_widget: Any, markdown_text: str) -> None:
    """Render Markdown inside an output widget and cache the raw text."""

    cleaned_markdown = normalize_markdown_spacing(markdown_text)
    setattr(output_widget, "raw_markdown", cleaned_markdown)
    html_text = markdown.markdown(cleaned_markdown)
    setattr(output_widget, "rendered_html", html_text)
    if hasattr(output_widget, "set_html"):
        output_widget.set_html(html_text)
    else:  # pragma: no cover - compatibility fallback
        try:
            output_widget.config(state=tk.NORMAL)
            output_widget.delete("1.0", tk.END)
            output_widget.insert(tk.END, cleaned_markdown)
        except Exception:
            pass


def markdown_to_plain_text(markdown_text: str) -> str:
    """Convert Markdown to plain text for clipboard and API payloads."""

    if not markdown_text:
        return ""
    cleaned_markdown = normalize_markdown_spacing(markdown_text)
    return markdown.to_plain_text(cleaned_markdown)
