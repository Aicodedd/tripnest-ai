# TripNest AI: one container serves the API and the web app.
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY backend ./backend
COPY frontend ./frontend

RUN useradd --create-home --uid 10001 tripnest && chown -R tripnest /app
USER tripnest
WORKDIR /app/backend

EXPOSE 8000
# Apply database migrations, then serve. The pre-trained crowd model ships in backend/models.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
