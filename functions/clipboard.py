from __future__ import annotations

import sys
import tkinter as tk
from typing import Iterable, Optional


def set_clipboard_html(
    widget: tk.Misc,
    plain_text: str,
    html_text: str,
    cf_html: str,
) -> bool:
    """Populate the clipboard with plain text and HTML targets."""

    if sys.platform.startswith("win"):
        try:
            if _set_clipboard_html_windows(plain_text, cf_html):
                return True
        except Exception:
            # Fall back to Tk-based clipboard handling on any failure.
            pass

    return _set_clipboard_html_via_tk(widget, plain_text, html_text, cf_html)

def get_clipboard_html(widget: tk.Misc) -> Optional[str]:
    """Return the HTML fragment currently stored on the clipboard, if any."""

    html_data = _get_html_via_tk(widget)
    if html_data:
        fragment = _extract_cf_html_fragment(html_data)
        return fragment or html_data

    if sys.platform.startswith("win"):
        html_data = _get_html_windows()
        if html_data:
            fragment = _extract_cf_html_fragment(html_data)
            return fragment or html_data

    return None


def _get_html_via_tk(widget: tk.Misc) -> Optional[str]:
    targets: Iterable[str]
    try:
        tk_targets = widget.tk.call("clipboard", "types")
    except tk.TclError:
        tk_targets = ()
    if tk_targets:
        targets = widget.tk.splitlist(tk_targets)
    else:
        targets = ()

    preferred_order = ["text/html", "HTML Format", "text/_moz_htmlcontext"]
    seen = set()
    ordered_targets = []
    for candidate in preferred_order:
        if candidate in targets and candidate not in seen:
            ordered_targets.append(candidate)
            seen.add(candidate)
    for candidate in targets:
        if candidate not in seen:
            ordered_targets.append(candidate)
            seen.add(candidate)

    for target in ordered_targets or ("text/html", "HTML Format"):
        try:
            data = widget.tk.call("clipboard", "get", "-type", target)
        except tk.TclError:
            continue
        if data:
            return str(data)
    return None


def _extract_cf_html_fragment(raw_html: str) -> Optional[str]:
    if not raw_html:
        return None

    start_marker = "<!--StartFragment-->"
    end_marker = "<!--EndFragment-->"
    start_index = raw_html.find(start_marker)
    end_index = raw_html.find(end_marker)
    if start_index != -1 and end_index != -1:
        start_index += len(start_marker)
        return raw_html[start_index:end_index].strip()

    headers: dict[str, str] = {}
    for line in raw_html.splitlines():
        if not line.strip():
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        headers[key.strip()] = value.strip()

    def _parse_index(name: str) -> Optional[int]:
        value = headers.get(name)
        if value is None:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    start_fragment = _parse_index("StartFragment")
    end_fragment = _parse_index("EndFragment")
    if start_fragment is not None and end_fragment is not None and end_fragment > start_fragment:
        return raw_html[start_fragment:end_fragment].strip()

    start_html = _parse_index("StartHTML")
    end_html = _parse_index("EndHTML")
    if start_html is not None and end_html is not None and end_html > start_html:
        return raw_html[start_html:end_html].strip()

    return None


def _get_html_windows() -> Optional[str]:  # pragma: no cover - platform specific
    try:
        import ctypes
        from ctypes import wintypes
    except Exception:
        return None

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    register_format = getattr(user32, "RegisterClipboardFormatW")
    open_clipboard = getattr(user32, "OpenClipboard")
    close_clipboard = getattr(user32, "CloseClipboard")
    get_clipboard_data = getattr(user32, "GetClipboardData")
    global_lock = getattr(kernel32, "GlobalLock")
    global_unlock = getattr(kernel32, "GlobalUnlock")
    global_size = getattr(kernel32, "GlobalSize")

    register_format.argtypes = [wintypes.LPCWSTR]
    register_format.restype = wintypes.UINT
    open_clipboard.argtypes = [wintypes.HWND]
    open_clipboard.restype = wintypes.BOOL
    close_clipboard.argtypes = []
    close_clipboard.restype = wintypes.BOOL
    get_clipboard_data.argtypes = [wintypes.UINT]
    get_clipboard_data.restype = wintypes.HANDLE
    global_lock.argtypes = [wintypes.HGLOBAL]
    global_lock.restype = wintypes.LPVOID
    global_unlock.argtypes = [wintypes.HGLOBAL]
    global_unlock.restype = wintypes.BOOL
    global_size.argtypes = [wintypes.HGLOBAL]
    try:
        size_t_type = wintypes.SIZE_T  # type: ignore[attr-defined]
    except AttributeError:
        size_t_type = getattr(ctypes, "c_size_t")
    global_size.restype = size_t_type

    cf_html = register_format("HTML Format")
    if not cf_html:
        return None

    if not open_clipboard(None):
        return None

    try:
        handle = get_clipboard_data(cf_html)
        if not handle:
            return None

        pointer = global_lock(handle)
        if not pointer:
            return None

        try:
            size = int(global_size(handle))
            if size <= 0:
                return None
            raw_bytes = ctypes.string_at(pointer, size)
        finally:
            global_unlock(handle)

        if not raw_bytes:
            return None

        raw_string = raw_bytes.split(b"\x00", 1)[0].decode("utf-8", errors="ignore")
        return raw_string.strip() or None
    finally:
        close_clipboard()

def _set_clipboard_html_via_tk(
    widget: tk.Misc,
    plain_text: str,
    html_text: str,
    cf_html: str,
) -> bool:
    """Use Tk clipboard APIs to advertise HTML/plain text."""

    try:
        widget.clipboard_clear()
    except tk.TclError:
        return False

    success = False

    if plain_text:
        try:
            widget.clipboard_append(plain_text)
            success = True
        except tk.TclError:
            pass

    html_targets = (
        ("text/html", cf_html or html_text),
        ("HTML Format", cf_html or html_text),
    )
    for target, payload in html_targets:
        if not payload:
            continue
        try:
            widget.clipboard_append(payload, type=target)
            success = True
        except tk.TclError:
            continue

    if not success and (html_text or cf_html):
        try:
            widget.clipboard_append(html_text or cf_html)
            success = True
        except tk.TclError:
            pass

    return success


def _set_clipboard_html_windows(plain_text: str, cf_html: str) -> bool:  # pragma: no cover - platform specific
    import ctypes
    from ctypes import wintypes

    GMEM_MOVEABLE = 0x0002
    CF_UNICODETEXT = 13

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    register_format = getattr(user32, "RegisterClipboardFormatW")
    open_clipboard = getattr(user32, "OpenClipboard")
    empty_clipboard = getattr(user32, "EmptyClipboard")
    close_clipboard = getattr(user32, "CloseClipboard")
    set_clipboard_data = getattr(user32, "SetClipboardData")
    global_alloc = getattr(kernel32, "GlobalAlloc")
    global_lock = getattr(kernel32, "GlobalLock")
    global_unlock = getattr(kernel32, "GlobalUnlock")
    global_free = getattr(kernel32, "GlobalFree")

    register_format.argtypes = [wintypes.LPCWSTR]
    register_format.restype = wintypes.UINT
    open_clipboard.argtypes = [wintypes.HWND]
    open_clipboard.restype = wintypes.BOOL
    empty_clipboard.argtypes = []
    empty_clipboard.restype = wintypes.BOOL
    close_clipboard.argtypes = []
    close_clipboard.restype = wintypes.BOOL
    set_clipboard_data.argtypes = [wintypes.UINT, wintypes.HANDLE]
    set_clipboard_data.restype = wintypes.HANDLE
    try:
        size_t_type = wintypes.SIZE_T  # type: ignore[attr-defined]
    except AttributeError:  # pragma: no cover - python < 3.8 fallback
        size_t_type = getattr(ctypes, "c_size_t")
    global_alloc.argtypes = [wintypes.UINT, size_t_type]
    global_alloc.restype = wintypes.HGLOBAL
    global_lock.argtypes = [wintypes.HGLOBAL]
    global_lock.restype = wintypes.LPVOID
    global_unlock.argtypes = [wintypes.HGLOBAL]
    global_unlock.restype = wintypes.BOOL
    global_free.argtypes = [wintypes.HGLOBAL]
    global_free.restype = wintypes.HGLOBAL

    html_format = register_format("HTML Format")
    if not html_format:
        return False

    if not open_clipboard(None):
        return False

    try:
        if not empty_clipboard():
            return False

        def _store_clipboard_data(format_id: int, payload: bytes) -> bool:
            handle = global_alloc(GMEM_MOVEABLE, len(payload))
            if not handle:
                return False
            pointer = global_lock(handle)
            if not pointer:
                global_free(handle)
                return False
            ctypes.memmove(pointer, payload, len(payload))
            global_unlock(handle)
            if not set_clipboard_data(format_id, handle):
                global_free(handle)
                return False
            return True

        if plain_text:
            text_bytes = plain_text.encode("utf-16-le") + b"\x00\x00"
            if not _store_clipboard_data(CF_UNICODETEXT, text_bytes):
                return False

        if cf_html:
            html_bytes = cf_html.encode("utf-8") + b"\x00"
            if not _store_clipboard_data(html_format, html_bytes):
                return False

        return bool(cf_html)
    finally:
        close_clipboard()