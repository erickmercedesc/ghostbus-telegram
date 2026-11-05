import uvicorn

from telegram_engine.core.config import get_settings
from telegram_engine.main import create_app

app = create_app()

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run("telegram_engine.__main__:app", host="0.0.0.0", port=settings.port, reload=False)
