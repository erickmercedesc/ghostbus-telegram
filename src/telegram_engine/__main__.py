import uvicorn

from telegram_engine.main import create_app

app = create_app()

if __name__ == "__main__":
    uvicorn.run("telegram_engine.__main__:app", host="0.0.0.0", port=8000, reload=False)
