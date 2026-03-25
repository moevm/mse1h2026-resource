from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from neo4j import ManagedTransaction

from app.repositories.neo4j_connection import neo4j_driver

log = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def register_application(
    name: str,
    description: Optional[str] = None,
    owner: Optional[str] = None,
) -> Dict[str, Any]:
    app_id = str(uuid.uuid4())
    app_token = str(uuid.uuid4())
    now = _now_iso()

    with neo4j_driver.session() as session:
        result = session.execute_write(
            _register_app_tx, app_id, app_token, name, description, owner, now
        )
    return result


def _register_app_tx(
    tx: ManagedTransaction,
    app_id: str,
    app_token: str,
    name: str,
    description: Optional[str],
    owner: Optional[str],
    now: str,
) -> Dict[str, Any]:
    result = tx.run(
        "MERGE (app:Application {name: $name}) "
        "ON CREATE SET "
        "    app.app_id = $app_id, "
        "    app.app_token = $app_token, "
        "    app.description = $description, "
        "    app.owner = $owner, "
        "    app.created_at = $now "
        "RETURN app",
        name=name,
        app_id=app_id,
        app_token=app_token,
        description=description,
        owner=owner,
        now=now,
    )
    record = result.single()
    return dict(record["app"])


def get_by_token(app_token: str) -> Optional[Dict[str, Any]]:
    with neo4j_driver.session() as session:
        return session.execute_read(_get_by_token_tx, app_token)


def _get_by_token_tx(tx: ManagedTransaction, app_token: str) -> Optional[Dict[str, Any]]:
    result = tx.run(
        "MATCH (app:Application {app_token: $app_token}) RETURN app",
        app_token=app_token,
    )
    record = result.single()
    return dict(record["app"]) if record else None


def get_by_id(app_id: str) -> Optional[Dict[str, Any]]:
    with neo4j_driver.session() as session:
        return session.execute_read(_get_by_id_tx, app_id)


def _get_by_id_tx(tx: ManagedTransaction, app_id: str) -> Optional[Dict[str, Any]]:
    result = tx.run(
        "MATCH (app:Application {app_id: $app_id}) RETURN app",
        app_id=app_id,
    )
    record = result.single()
    return dict(record["app"]) if record else None


def list_applications() -> List[Dict[str, Any]]:
    with neo4j_driver.session() as session:
        return session.execute_read(_list_apps_tx)


def _list_apps_tx(tx: ManagedTransaction) -> List[Dict[str, Any]]:
    result = tx.run(
        "MATCH (app:Application) "
        "OPTIONAL MATCH (app)-[:HAS_AGENT]->(a:Agent) "
        "RETURN app, count(a) AS agent_count "
        "ORDER BY app.created_at DESC"
    )
    apps = []
    for record in result:
        app_data = dict(record["app"])
        app_data["agent_count"] = record["agent_count"]
        apps.append(app_data)
    return apps


def get_application_detail(app_id: str) -> Optional[Dict[str, Any]]:
    with neo4j_driver.session() as session:
        return session.execute_read(_get_detail_tx, app_id)


def _get_detail_tx(tx: ManagedTransaction, app_id: str) -> Optional[Dict[str, Any]]:
    result = tx.run(
        "MATCH (app:Application {app_id: $app_id}) "
        "OPTIONAL MATCH (app)-[:HAS_AGENT]->(a:Agent) "
        "RETURN app, collect(a) AS agents",
        app_id=app_id,
    )
    record = result.single()
    if not record:
        return None

    app_data = dict(record["app"])
    app_data["agents"] = [dict(a) for a in record["agents"] if a is not None]
    return app_data


def bind_agent_to_application(app_id: str, agent_id: str) -> bool:
    with neo4j_driver.session() as session:
        return session.execute_write(_bind_agent_tx, app_id, agent_id)


def _bind_agent_tx(tx: ManagedTransaction, app_id: str, agent_id: str) -> bool:
    result = tx.run(
        "MATCH (app:Application {app_id: $app_id}) "
        "MATCH (agent:Agent {agent_id: $agent_id}) "
        "MERGE (app)-[:HAS_AGENT]->(agent) "
        "RETURN agent",
        app_id=app_id,
        agent_id=agent_id,
    )
    return result.single() is not None


def get_agent_ids_for_application(app_id: str) -> List[str]:
    with neo4j_driver.session() as session:
        return session.execute_read(_get_agent_ids_tx, app_id)


def _get_agent_ids_tx(tx: ManagedTransaction, app_id: str) -> List[str]:
    result = tx.run(
        "MATCH (app:Application {app_id: $app_id})-[:HAS_AGENT]->(a:Agent) "
        "RETURN a.agent_id AS agent_id",
        app_id=app_id,
    )
    return [r["agent_id"] for r in result]


def get_agent_names_for_application(app_id: str) -> List[str]:
    with neo4j_driver.session() as session:
        return session.execute_read(_get_agent_names_tx, app_id)


def _get_agent_names_tx(tx: ManagedTransaction, app_id: str) -> List[str]:
    result = tx.run(
        "MATCH (app:Application {app_id: $app_id})-[:HAS_AGENT]->(a:Agent) "
        "RETURN a.name AS name",
        app_id=app_id,
    )
    return [r["name"] for r in result]


def ensure_application_indexes() -> None:
    with neo4j_driver.session() as session:
        session.run(
            "CREATE CONSTRAINT app_token_unique IF NOT EXISTS "
            "FOR (app:Application) REQUIRE app.app_token IS UNIQUE"
        )
        session.run(
            "CREATE CONSTRAINT app_name_unique IF NOT EXISTS "
            "FOR (app:Application) REQUIRE app.name IS UNIQUE"
        )
        session.run(
            "CREATE CONSTRAINT app_id_unique IF NOT EXISTS "
            "FOR (app:Application) REQUIRE app.app_id IS UNIQUE"
        )
    log.info("Application indexes ensured")
