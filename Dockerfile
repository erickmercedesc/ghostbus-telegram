FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml /app/
COPY src /app/src
RUN pip install --no-cache-dir .
COPY . /app

ENV PYTHONPATH=/app/src
CMD ["python", "-m", "telegram_engine"]
