# TripNest AI on Hugging Face Spaces (Docker SDK): one container serves the API and the web app.
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
# Spaces run the container as user 1000 and only /tmp is reliably writable.
RUN useradd -m -u 1000 user
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY backend ./backend
COPY frontend ./frontend
RUN chown -R user /app
USER user
WORKDIR /app/backend

ENV ENV=production PHOTO_PROVIDER=wikimedia APP_TZ=Asia/Kolkata PORT=7860
EXPOSE 7860
# The product has no accounts or sessions, so SECRET_KEY only has to satisfy the production check.
# Use the Space secret if one is set; otherwise generate a random key per start. The catalogue is
# read-only reference data seeded at start-up into a throw-away SQLite file; nothing needs to persist.
CMD ["sh", "-c", "export DATABASE_URL=sqlite:////tmp/tripnest.db; export SECRET_KEY=${SECRET_KEY:-$(python -c 'import secrets;print(secrets.token_urlsafe(48))')}; exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
