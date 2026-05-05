FROM python:3.12-slim

WORKDIR /app
COPY watcher.py .

RUN pip install --no-cache-dir fastapi uvicorn requests

EXPOSE 8090
CMD ["python", "watcher.py"]
