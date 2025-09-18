"""Utility helpers for working with local files."""

from __future__ import annotations

import os

import PyPDF2
from docx import Document


def extract_text_from_file(path: str) -> str:
    """Return plain text content from the supported file ``path``.

    The helper mirrors the behaviour previously embedded inside
    :mod:`gui.main_window` and is now shared with the invoice view so both
    windows keep identical attachment handling logic.
    """

    ext = os.path.splitext(path)[1].lower()
    if ext == ".txt":
        with open(path, "r", encoding="utf-8") as file:
            return file.read()
    if ext == ".pdf":
        with open(path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            return "\n".join(page.extract_text() or "" for page in reader.pages)
    if ext == ".docx":
        document = Document(path)
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    return ""

