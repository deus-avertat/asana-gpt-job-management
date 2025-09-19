from __future__ import annotations

import os
import tkinter as tk
from tkinter import messagebox
from typing import Any

from docx import Document

import PyPDF2

from vendor_setup import ensure_vendor_path

ensure_vendor_path()

import markdown


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
