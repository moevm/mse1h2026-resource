FROM python:3.12-slim

WORKDIR /app
COPY watcher.py .

RUN pip install --no-cache-dir kubernetes requests \
    && adduser --disabled-password --gecos "" appuser \
    && chown -R appuser:appuser /app
USER appuser

CMD ["python", "watcher.py"]
