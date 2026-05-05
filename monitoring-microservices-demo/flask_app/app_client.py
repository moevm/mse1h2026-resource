import logging
from flask import (
  Flask
)

import requests
import os
from opentelemetry import trace

app = Flask(__name__)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

FASTAPI_URL=os.environ.get("FASTAPI_URL", "http://localhost:8000")
GOLANG_URL=os.environ.get("GOLANG_URL", "http://localhost:8002")

@app.route("/")
def index():
    logger.info("hello-world")
    return "hello-world"


@app.route("/external")
def call_external_api():
    span = trace.get_current_span()
    span.set_attribute("external_api", "example.com")
    try:
        res = requests.get("http://example.com", timeout=1)
        return {"status_code": res.status_code, "external_api": "example.com"}, res.status_code
    except requests.RequestException as exc:
        logger.warning("external api request failed: %s", exc)
        return {"status_code": 502, "external_api": "example.com"}, 502


@app.route("/users")
def show_all_users():
    res = requests.get(f"{FASTAPI_URL}/users")
    return res.json(), res.status_code


@app.route("/albums")
def show_all_albums():
    res = requests.get(f"{GOLANG_URL}/albums")
    return res.json(), res.status_code


@app.route("/user/<username>")
def show_user_profile(username):
    res = requests.get(f"{FASTAPI_URL}/users/", params={"name": username})
    return res.json(), res.status_code


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001)
