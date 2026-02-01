FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Usar Gunicorn con workers Uvicorn para mejor rendimiento en producción
CMD ["sh", "-c", "exec gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8080} --timeout 300"]
