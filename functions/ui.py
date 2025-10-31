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

from functions.clipboard import get_clipboard_html

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

def copy_output(tk_root, output_text):
    print("INFO: Copied Output to Clipboard")
    tk_root.clipboard_clear()
    markdown_text = get_widget_markdown(output_text)
    tk_root.clipboard_append(markdown_text)
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