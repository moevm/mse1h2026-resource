import logging
import os
import random
import threading
import time

import requests
from flask import Flask, jsonify, request
from opentelemetry import trace

app = Flask(__name__)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

FASTAPI_URL = os.environ.get("FASTAPI_URL", "http://localhost:8000")
GOLANG_URL = os.environ.get("GOLANG_URL", "http://localhost:8002")

tracer = trace.get_tracer(__name__)

ATTR_PEER_SERVICE = "peer.service"
ATTR_EXTERNAL_API = "external_api"
ATTR_MSG_DEST = "messaging.destination"
ATTR_MSG_OP = "messaging.operation"

SVC_USER = "fastapi-app"
SVC_PRODUCT = "golang-app"
EXT_STRIPE = "stripe.com"
EXT_ANALYTICS = "analytics.mixpanel.com"
EXT_ML = "ml.recommendations.internal"
QUEUE_ORDERS = "order-events"
QUEUE_NOTIFICATIONS = "notification-events"

ERR_USER_SVC = "user-service unavailable"
ERR_PRODUCT_SVC = "product-service unavailable"


@app.route("/")
def index():
    return jsonify({"service": "api-gateway", "version": "2.1.0", "status": "healthy"})


@app.route("/health")
def health():
    return jsonify({"status": "healthy"})


@app.route("/api/v1/users", methods=["GET"])
def list_users():
    span = trace.get_current_span()
    span.set_attribute(ATTR_PEER_SERVICE, SVC_USER)
    try:
        res = requests.get(f"{FASTAPI_URL}/users", timeout=5)
        return jsonify(res.json()), res.status_code
    except Exception as e:
        logger.error("%s: %s", ERR_USER_SVC, e)
        return jsonify({"error": ERR_USER_SVC}), 503


@app.route("/api/v1/users/<username>", methods=["GET"])
def get_user(username):
    span = trace.get_current_span()
    span.set_attribute(ATTR_PEER_SERVICE, SVC_USER)
    try:
        res = requests.get(f"{FASTAPI_URL}/users/", params={"name": username}, timeout=5)
        return jsonify(res.json()), res.status_code
    except Exception as e:
        logger.error("%s: %s", ERR_USER_SVC, e)
        return jsonify({"error": ERR_USER_SVC}), 503


@app.route("/api/v1/users", methods=["POST"])
def create_user():
    span = trace.get_current_span()
    span.set_attribute(ATTR_PEER_SERVICE, SVC_USER)
    try:
        body = request.get_json(silent=True) or {}
        res = requests.post(f"{FASTAPI_URL}/users", json=body, timeout=5)
        ct = res.headers.get("content-type", "")
        data = res.json() if ct.startswith("application/json") else {}
        return jsonify(data), res.status_code
    except Exception as e:
        logger.error("%s: %s", ERR_USER_SVC, e)
        return jsonify({"error": ERR_USER_SVC}), 503


@app.route("/api/v1/products", methods=["GET"])
def list_products():
    span = trace.get_current_span()
    span.set_attribute(ATTR_PEER_SERVICE, SVC_PRODUCT)
    try:
        res = requests.get(f"{GOLANG_URL}/albums", timeout=5)
        return jsonify(res.json()), res.status_code
    except Exception as e:
        logger.error("%s: %s", ERR_PRODUCT_SVC, e)
        return jsonify({"error": ERR_PRODUCT_SVC}), 503


@app.route("/api/v1/products/<product_id>", methods=["GET"])
def get_product(product_id):
    span = trace.get_current_span()
    span.set_attribute(ATTR_PEER_SERVICE, SVC_PRODUCT)
    try:
        res = requests.get(f"{GOLANG_URL}/albums/{product_id}", timeout=5)
        return jsonify(res.json()), res.status_code
    except Exception as e:
        logger.error("%s: %s", ERR_PRODUCT_SVC, e)
        return jsonify({"error": ERR_PRODUCT_SVC}), 503


@app.route("/api/v1/orders", methods=["GET", "POST"])
def handle_orders():
    """Orchestrate order: verify user, get product, process payment, publish event."""
    span = trace.get_current_span()

    span.set_attribute(ATTR_PEER_SERVICE, SVC_USER)
    try:
        requests.get(f"{FASTAPI_URL}/users", timeout=5)
    except Exception:
        pass

    span.set_attribute(ATTR_PEER_SERVICE, SVC_PRODUCT)
    try:
        product_res = requests.get(f"{GOLANG_URL}/albums", timeout=5)
        products = product_res.json() if product_res.status_code == 200 else []
    except Exception:
        products = []

    span.set_attribute(ATTR_EXTERNAL_API, EXT_STRIPE)
    try:
        requests.post("https://api.stripe.com/v1/charges", timeout=1)
    except Exception:
        pass

    span.set_attribute(ATTR_MSG_DEST, QUEUE_ORDERS)
    span.set_attribute(ATTR_MSG_OP, "publish")

    order_id = f"ord-{random.randint(1000, 9999)}"
    logger.info("Order %s created", order_id)
    return jsonify({"order_id": order_id, "status": "created", "items": len(products)}), 201


@app.route("/api/v1/payments", methods=["POST"])
def process_payment():
    span = trace.get_current_span()
    span.set_attribute(ATTR_EXTERNAL_API, EXT_STRIPE)
    try:
        requests.post("https://api.stripe.com/v1/charges", timeout=1)
    except Exception:
        pass
    return jsonify({"payment_id": f"pay-{random.randint(1000, 9999)}", "status": "completed"}), 200


@app.route("/api/v1/payments/health", methods=["GET"])
def payments_health():
    span = trace.get_current_span()
    span.set_attribute(ATTR_EXTERNAL_API, EXT_STRIPE)
    return jsonify({"gateway": "stripe", "status": "connected"})


@app.route("/api/v1/notifications", methods=["POST"])
def send_notification():
    span = trace.get_current_span()
    span.set_attribute(ATTR_MSG_DEST, QUEUE_NOTIFICATIONS)
    span.set_attribute(ATTR_MSG_OP, "publish")
    return jsonify({"notification_id": f"notif-{random.randint(1000, 9999)}", "status": "queued"}), 202


@app.route("/api/v1/analytics", methods=["GET"])
def get_analytics():
    span = trace.get_current_span()
    span.set_attribute(ATTR_EXTERNAL_API, EXT_ANALYTICS)
    try:
        requests.get("http://example.com", timeout=2)
    except Exception:
        pass
    return jsonify({"active_users": random.randint(100, 500), "requests_today": random.randint(1000, 5000)}), 200


@app.route("/api/v1/recommendations", methods=["GET"])
def get_recommendations():
    """Get personalized recommendations — calls User Service + Product Service + ML."""
    span = trace.get_current_span()

    span.set_attribute(ATTR_PEER_SERVICE, SVC_USER)
    try:
        requests.get(f"{FASTAPI_URL}/users", timeout=5)
    except Exception:
        pass

    span.set_attribute(ATTR_PEER_SERVICE, SVC_PRODUCT)
    try:
        product_res = requests.get(f"{GOLANG_URL}/albums", timeout=5)
        products = product_res.json() if product_res.status_code == 200 else []
    except Exception:
        products = []

    span.set_attribute(ATTR_EXTERNAL_API, EXT_ML)

    recommended = random.sample(products, min(3, len(products))) if products else []
    return jsonify({"recommendations": recommended}), 200


def _generate_traffic():
    """Background thread generating realistic traffic patterns."""
    time.sleep(20)
    endpoints = [
        ("GET", "/api/v1/users"),
        ("GET", "/api/v1/products"),
        ("GET", "/api/v1/users/testuser"),
        ("GET", "/api/v1/products/1"),
        ("POST", "/api/v1/orders"),
        ("GET", "/api/v1/analytics"),
        ("POST", "/api/v1/notifications"),
        ("GET", "/api/v1/recommendations"),
        ("GET", "/api/v1/payments/health"),
    ]
    while True:
        try:
            method, path = random.choice(endpoints)
            url = f"http://localhost:8001{path}"
            resp = requests.request(method, url, timeout=5)
            logger.info("Traffic: %s %s -> %d", method, path, resp.status_code)
        except Exception as e:
            logger.debug("Traffic gen: %s", e)
        time.sleep(random.uniform(3, 10))


if __name__ == "__main__":
    thread = threading.Thread(target=_generate_traffic, daemon=True)
    thread.start()
    app.run(host="0.0.0.0", port=8001)
