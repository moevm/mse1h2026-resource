from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from neo4j import ManagedTransaction

from app.repositories.neo4j_connection import neo4j_driver

log = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def register_agent(
    name: str,
    source_type: str,
    description: Optional[str] = None,
    app_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    agent_id = str(uuid.uuid4())
    token = str(uuid.uuid4())
    now = _now_iso()

    with neo4j_driver.session() as session:
        result = session.execute_write(
            _register_tx, agent_id, token, name, source_type, description, now, app_id, user_id
        )
    return result


def _register_tx(
    tx: ManagedTransaction,
    agent_id: str,
    token: str,
    name: str,
    source_type: str,
    description: Optional[str],
    now: str,
    app_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    # MERGE by (name, user_id) so different users can have agents with the same name
    if app_id:
        result = tx.run(
            "MERGE (a:Agent {name: $name, user_id: $user_id}) "
            "ON CREATE SET "
            "    a.agent_id = $agent_id, "
            "    a.token = $token, "
            "    a.source_type = $source_type, "
            "    a.description = $description, "
            "    a.registered_at = $now, "
            "    a.app_id = $app_id "
            "SET a.last_seen_at = $now "
            "WITH a "
            "MATCH (app:Application {app_id: $app_id}) "
            "MERGE (app)-[:HAS_AGENT]->(a) "
            "RETURN a",
            name=name,
            agent_id=agent_id,
            token=token,
            source_type=source_type,
            description=description,
            now=now,
            app_id=app_id,
            user_id=user_id,
        )
    else:
        result = tx.run(
            "MERGE (a:Agent {name: $name, user_id: $user_id}) "
            "ON CREATE SET "
            "    a.agent_id = $agent_id, "
            "    a.token = $token, "
            "    a.source_type = $source_type, "
            "    a.description = $description, "
            "    a.registered_at = $now "
            "SET a.last_seen_at = $now "
            "RETURN a",
            name=name,
            agent_id=agent_id,
            token=token,
            source_type=source_type,
            description=description,
            now=now,
            user_id=user_id,
        )
    record = result.single()
    return dict(record["a"])


def update_last_seen(token: str) -> None:
    with neo4j_driver.session() as session:
        session.execute_write(_update_last_seen_tx, token, _now_iso())


def _update_last_seen_tx(tx: ManagedTransaction, token: str, now: str) -> None:
    tx.run(
        "MATCH (a:Agent {token: $token}) SET a.last_seen_at = $now",
        token=token,
        now=now,
    )


def get_by_token(token: str) -> Optional[Dict[str, Any]]:
    with neo4j_driver.session() as session:
        return session.execute_read(_get_by_token_tx, token)


def _get_by_token_tx(tx: ManagedTransaction, token: str) -> Optional[Dict[str, Any]]:
    result = tx.run(
        "MATCH (a:Agent {token: $token}) RETURN a",
        token=token,
    )
    record = result.single()
    return dict(record["a"]) if record else None


def list_agents(user_id: Optional[str] = None) -> list[Dict[str, Any]]:
    with neo4j_driver.session() as session:
        return session.execute_read(_list_agents_tx, user_id)


def _list_agents_tx(tx: ManagedTransaction, user_id: Optional[str]) -> list[Dict[str, Any]]:
    if user_id is None:
        result = tx.run(
            "MATCH (a:Agent) "
            "OPTIONAL MATCH (app:Application)-[:HAS_AGENT]->(a) "
            "RETURN a, app.name AS app_name, app.app_id AS app_id "
            "ORDER BY a.registered_at DESC"
        )
    else:
        result = tx.run(
            "MATCH (a:Agent {user_id: $user_id}) "
            "OPTIONAL MATCH (app:Application)-[:HAS_AGENT]->(a) "
            "RETURN a, app.name AS app_name, app.app_id AS app_id "
            "ORDER BY a.registered_at DESC",
            user_id=user_id,
        )
    agents = []
    for record in result:
        agent_data = dict(record["a"])
        agent_data["app_name"] = record["app_name"]
        agent_data["app_id"] = record["app_id"]
        agents.append(agent_data)
    return agents


def get_agent_names_for_user(user_id: str) -> list[str]:
    with neo4j_driver.session() as session:
        result = session.run(
            "MATCH (a:Agent {user_id: $user_id}) RETURN a.name AS name",
            user_id=user_id,
        )
        return [r["name"] for r in result]


def ensure_agent_indexes() -> None:
    with neo4j_driver.session() as session:
        # Old global name constraint cannot coexist with multi-user agents.
        session.run("DROP CONSTRAINT agent_name_unique IF EXISTS")
        session.run(
            "CREATE CONSTRAINT agent_token_unique IF NOT EXISTS "
            "FOR (a:Agent) REQUIRE a.token IS UNIQUE"
        )
        session.run(
            "CREATE INDEX agent_user_idx IF NOT EXISTS "
            "FOR (a:Agent) ON (a.user_id)"
        )
    log.info("Agent indexes ensured")