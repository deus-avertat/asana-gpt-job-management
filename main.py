import json
import os
import sys

try:
    from tkinter import messagebox
except Exception:
    messagebox = None

from vendor_setup import ensure_vendor_path

ensure_vendor_path()

from gui.main_window import create_main_window
from services.openai_service import OpenAIService

REQUIRED_CONFIG_KEYS = [
    "openai_api_key",
    "asana_token",
    "asana_project_id",
    "asana_workspace",
]

def _show_config_error(message: str) -> None:
    if messagebox is not None:
        try:
            messagebox.showerror("Configuration Error", message)
            return
        except Exception:
            # Fallback to console output if messagebox cannot be displayed
            pass

    print(f"Configuration Error: {message}", file=sys.stderr)

def validate_config(config: dict) -> list[str]:
    invalid_keys = []

    for key in REQUIRED_CONFIG_KEYS:
        value = config.get(key)
        if value is None or (isinstance(value, str) and not value.strip()):
            invalid_keys.append(key)

    return invalid_keys

def main() -> None:
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        _show_config_error(
            "Configuration file not found. Please create config.json from"
            " config.example.json."
        )
        sys.exit(1)
    except json.JSONDecodeError as exc:
        _show_config_error(f"Configuration file is malformed: {exc}")
        sys.exit(1)

    invalid_keys = validate_config(config)
    if invalid_keys:
        _show_config_error(
            "Missing or empty required config keys: "
            f"{', '.join(invalid_keys)}. "
            "Please update config.json using config.example.json as a template."
        )
        sys.exit(1)

    openai_service = OpenAIService(config["openai_api_key"])
    create_main_window(openai_service, config)


if __name__ == "__main__":
    main()
