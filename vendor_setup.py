from __future__ import annotations

import os
import sys


def ensure_vendor_path() -> None:
    """Add the local ``vendor`` directory to ``sys.path`` if present."""
    vendor_dir = os.path.join(os.path.dirname(__file__), "vendor")
    if os.path.isdir(vendor_dir) and vendor_dir not in sys.path:
        sys.path.insert(0, vendor_dir)
