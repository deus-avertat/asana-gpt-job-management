import json
import os

from vendor_setup import ensure_vendor_path

ensure_vendor_path()

from gui.main_window import create_main_window
from services.openai_service import OpenAIService


def main() -> None:
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    with open(config_path, "r") as f:
        config = json.load(f)

    openai_service = OpenAIService(config["openai_api_key"])
    create_main_window(openai_service, config)


if __name__ == "__main__":
    main()
