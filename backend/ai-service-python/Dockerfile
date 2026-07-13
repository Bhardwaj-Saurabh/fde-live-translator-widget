# Build context is the ASSIGNMENT ROOT (fly.ai-service.toml lives there).
FROM python:3.12-slim

WORKDIR /app

COPY backend/ai-service-python/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ai-service-python/ .

# SQLite cache lives on the mounted Fly volume so it survives restarts/deploys
ENV TRANSLATION_DB_PATH=/data/translations.db

EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
