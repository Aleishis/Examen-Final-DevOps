FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

RUN useradd --create-home --uid 1000 app
COPY --chown=app:app . .
RUN mkdir -p /app/static/uploads && chown app:app /app/static/uploads

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/health', timeout=4)"

# Un solo worker con hilos porque Flask-SocketIO guarda las salas en memoria
CMD gunicorn --workers 1 --threads 100 --bind 0.0.0.0:${PORT} main:app
