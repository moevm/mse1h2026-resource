import uvicorn
from fastapi import FastAPI, HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
import os
import logging
import json

from random import randint, choice
from time import sleep
import time

from instrumentation import (
    instrument_logging,
    instrument_tracing,
    instrument_metrics,
    instrument_database,
    instrument_profiling,
)

from sqlmodel import select
from db import engine, Session, create_db_and_tables
from models import Users
import pyroscope
from opentelemetry import trace
from opentelemetry.trace import format_trace_id

import redis

service_name = "fastapi-app"
otlp_endpoint = os.environ.get("OTLP_GRPC_ENDPOINT", "http://localhost:4317")
pyroscope_endpoint = os.environ.get("PYROSCOPE_ENDPOINT", "http://localhost:4040")
redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

redis_client = redis.from_url(redis_url, decode_responses=True)

ATTR_DB_TABLE = "db.table"
ATTR_DB_OP = "db.operation"
ATTR_CACHE = "cache_name"
CACHE_NAME = "user-sessions"
CACHE_KEY_ALL = "users:all"


class PyroscopeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        trace_id = format_trace_id(trace.get_current_span().get_span_context().trace_id)
        with pyroscope.tag_wrapper({"endpoint": path, "trace_id": trace_id}):
            start_time = time.time()
            response = await call_next(request)
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)
        return response


app = FastAPI()
app.add_middleware(PyroscopeMiddleware)

pyroscope.configure(
    application_name=service_name,
    server_address=pyroscope_endpoint,
    enable_logging=True,
)

# Instrument tracing
tracer = instrument_tracing(
    app=app,
    service_name=service_name,
    otlp_endpoint=otlp_endpoint,
    excluded_urls="/metrics",
)

# Instrument profiling
tracer = instrument_profiling(tracer=tracer)

# Instrument logging
handler = instrument_logging(service_name=service_name, otlp_endpoint=otlp_endpoint)

# Attach OTLP handler to root logger
logging.getLogger().addHandler(handler)

# Send test message to log
logging.info(f"{service_name} started, listening on port 8000")

# Instrument metrics
instrument_metrics(app=app)

# Instrument database
instrument_database(engine=engine, tracer=tracer)

# Create database and tables in database
create_db_and_tables()

# Seed demo data
with Session(engine) as session:
    if not session.exec(select(Users)).first():
        demo_users = [
            Users(name="alice", age=28),
            Users(name="bob", age=35),
            Users(name="charlie", age=42),
            Users(name="diana", age=24),
            Users(name="eve", age=31),
        ]
        for u in demo_users:
            session.add(u)
        session.commit()
        logging.info("Seeded %d demo users", len(demo_users))


@app.get("/")
def root_endpoint():
    return {"service": service_name, "version": "2.1.0", "status": "healthy"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/users", response_model=list[Users])
def read_users():
    span = trace.get_current_span()

    # Simulate slow query in 10% of cases
    if randint(1, 10) == 10:
        logging.warning("slow query detected on users table")
        do_long_work(10)

    # Simulate error in 10% of cases
    if randint(1, 10) == 9:
        logging.error("database query failed")
        raise HTTPException(status_code=500, detail="Internal server error")

    # Check Redis cache first
    span.set_attribute("cache_name", CACHE_NAME)
    cached = redis_client.get(CACHE_KEY_ALL)
    if cached:
        logging.info("cache HIT for users:all")
        return json.loads(cached)

    logging.info("cache MISS for users:all, querying database")
    span.set_attribute(ATTR_DB_TABLE, "users")
    span.set_attribute(ATTR_DB_OP, "SELECT")

    with Session(engine) as session:
        users = session.exec(select(Users)).all()
        result = [{"id": u.id, "name": u.name, "age": u.age} for u in users]

    # Write to cache
    redis_client.setex(CACHE_KEY_ALL, 30, json.dumps(result))
    return result


@app.get("/users/{user_id}")
def read_user(user_id: int):
    span = trace.get_current_span()
    span.set_attribute("cache_name", CACHE_NAME)
    span.set_attribute(ATTR_DB_TABLE, "users")
    span.set_attribute(ATTR_DB_OP, "SELECT")

    # Check cache
    cached = redis_client.get(f"users:{user_id}")
    if cached:
        logging.info("cache HIT for users:%d", user_id)
        return json.loads(cached)

    with Session(engine) as session:
        user = session.get(Users, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        result = {"id": user.id, "name": user.name, "age": user.age}

    redis_client.setex(f"users:{user_id}", 60, json.dumps(result))
    return result


@app.post("/users")
def create_user(user: Users):
    span = trace.get_current_span()
    span.set_attribute(ATTR_DB_TABLE, "users")
    span.set_attribute(ATTR_DB_OP, "INSERT")

    with Session(engine) as session:
        session.add(user)
        session.commit()
        session.refresh(user)

    # Invalidate cache
    span.set_attribute("cache_name", CACHE_NAME)
    redis_client.delete(CACHE_KEY_ALL)

    logging.info("Created user: %s (id=%d)", user.name, user.id)
    return {"id": user.id, "name": user.name, "age": user.age}


@app.delete("/users/{user_id}")
def delete_user(user_id: int):
    span = trace.get_current_span()
    span.set_attribute(ATTR_DB_TABLE, "users")
    span.set_attribute(ATTR_DB_OP, "DELETE")

    with Session(engine) as session:
        user = session.get(Users, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        session.delete(user)
        session.commit()

    span.set_attribute("cache_name", CACHE_NAME)
    redis_client.delete(CACHE_KEY_ALL, f"users:{user_id}")

    logging.info("Deleted user id=%d", user_id)
    return {"deleted": user_id}


@app.get("/do_long_work")
def do_long_work(sec: int = 0):
    x = randint(1000, 10000)
    timeout = time.time() + float(sec)
    while True:
        if time.time() > timeout:
            break
        x * x
    return {"worked_seconds": sec}


if __name__ == "__main__":
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["access"][
        "fmt"
    ] = "%(asctime)s %(levelname)s [%(name)s] [%(filename)s:%(lineno)d] [trace_id=%(otelTraceID)s span_id=%(otelSpanID)s resource.service.name=%(otelServiceName)s] - %(message)s"
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=log_config)
