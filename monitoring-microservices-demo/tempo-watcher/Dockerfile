FROM python:3.12-slim

WORKDIR /app
COPY tempo_watcher.py register.py ./

RUN pip install --no-cache-dir fastapi uvicorn requests \
    && adduser --disabled-password --gecos "" appuser \
    && mkdir -p /data \
    && chown -R appuser:appuser /app /data
USER appuser
VOLUME ["/data"]

EXPOSE 8091
CMD ["python", "tempo_watcher.py"]
