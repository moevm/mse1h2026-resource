FROM python:3.12-slim

WORKDIR /app
COPY watcher.py .

RUN pip install --no-cache-dir fastapi uvicorn requests \
    && adduser --disabled-password --gecos "" appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8090
CMD ["python", "watcher.py"]
