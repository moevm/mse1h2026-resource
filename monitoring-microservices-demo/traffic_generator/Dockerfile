FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir requests
COPY phased_generator.py .
RUN useradd -m appuser
USER appuser
CMD ["python", "phased_generator.py"]
