"""Write the live FastAPI OpenAPI document to swagger.json."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

from telegram_engine.core.config import Settings
from telegram_engine.main import create_app

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    app = create_app(
        settings=Settings(
            internal_api_key="export",
            session_encryption_key="x",
            telegram_api_id=1,
            telegram_api_hash="h",
        ),
        service=Mock(),
        restore_on_startup=False,
    )
    spec = app.openapi()
    target = ROOT / "swagger.json"
    target.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
