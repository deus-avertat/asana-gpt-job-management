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

    setattr(output_widget, "raw_markdown", markdown_text)
    html_text = markdown.markdown(markdown_text)
    if hasattr(output_widget, "set_html"):
        output_widget.set_html(html_text)
    else:  # pragma: no cover - compatibility fallback
        try:
            output_widget.config(state=tk.NORMAL)
            output_widget.delete("1.0", tk.END)
            output_widget.insert(tk.END, markdown_text)
        except Exception:
            pass


def markdown_to_plain_text(markdown_text: str) -> str:
    """Convert Markdown to plain text for clipboard and API payloads."""

    if not markdown_text:
        return ""
    return markdown.to_plain_text(markdown_text)
