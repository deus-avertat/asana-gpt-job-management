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


_BULLET_PREFIXES = {"•", "◦", "‣", "∙"}


def _is_list_item(line: str) -> bool:
    """Return ``True`` when *line* represents a Markdown list item."""

    stripped = line.lstrip()
    if not stripped:
        return False
    marker = stripped[0]
    if marker in "-*+" and (len(stripped) == 1 or stripped[1].isspace()):
        return True
    if marker in _BULLET_PREFIXES:
        remainder = stripped[1:]
        return not remainder or remainder[0].isspace()
    if marker.isdigit():
        index = 0
        length = len(stripped)
        while index < length and stripped[index].isdigit():
            index += 1
        if index and index < length and stripped[index] in {".", ")"}:
            index += 1
            if index == length or stripped[index].isspace():
                return True
    return False


def _looks_like_paragraph(line: str) -> bool:
    """Heuristically determine whether *line* represents a paragraph body."""

    stripped = line.strip()
    if not stripped:
        return False
    if stripped.startswith(("#", ">", "`", "|")):
        return False
    if _is_list_item(stripped):
        return False
    if stripped.endswith(":") and len(stripped) <= 40:
        return False
    words = stripped.split()
    if len(words) >= 8:
        return True
    return any(char in stripped for char in ".!?")


def _prepare_markdown_for_rendering(markdown_text: str) -> str:
    """Convert common bullet characters into Markdown list markers."""

    converted: list[str] = []
    for line in markdown_text.splitlines():
        stripped = line.lstrip()
        if not stripped:
            converted.append(line)
            continue
        marker = stripped[0]
        if marker in _BULLET_PREFIXES and (len(stripped) == 1 or stripped[1].isspace()):
            indent = line[: len(line) - len(stripped)]
            content = stripped[1:].lstrip()
            converted.append(f"{indent}- {content}" if content else f"{indent}-")
        else:
            converted.append(line)
    return "\n".join(converted)


def normalize_markdown_spacing(markdown_text: str) -> str:
    """Condense excessive blank lines while keeping Markdown structure."""

    if not markdown_text:
        return ""

    lines = markdown_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    normalized: list[str] = []
    blank_run = 0
    last_nonempty: str | None = None
    in_code_block = False

    for raw_line in lines:
        stripped = raw_line.strip()

        if stripped.startswith("```"):
            if blank_run and normalized:
                normalized.append("")
            blank_run = 0
            normalized.append(raw_line.rstrip())
            last_nonempty = raw_line.rstrip()
            in_code_block = not in_code_block
            continue

        if in_code_block:
            normalized.append(raw_line.rstrip())
            last_nonempty = raw_line.rstrip()
            continue

        if not stripped:
            blank_run += 1
            continue

        line = raw_line.rstrip()
        is_list_item = _is_list_item(line)
        if blank_run:
            prev_is_list = last_nonempty is not None and _is_list_item(last_nonempty)
            prev_is_paragraph = last_nonempty is not None and _looks_like_paragraph(last_nonempty)
            curr_is_paragraph = _looks_like_paragraph(line)
            if is_list_item:
                pass
            elif prev_is_list and curr_is_paragraph:
                normalized.append("")
            elif prev_is_paragraph and curr_is_paragraph:
                normalized.append("")
            blank_run = 0
        normalized.append(line)
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
    html_ready = _prepare_markdown_for_rendering(cleaned_markdown)
    html_text = markdown.markdown(html_ready)
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
    html_ready = _prepare_markdown_for_rendering(cleaned_markdown)
    return markdown.to_plain_text(html_ready)
