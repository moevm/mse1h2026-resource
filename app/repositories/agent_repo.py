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
) -> Dict[str, Any]:
    agent_id = str(uuid.uuid4())
    token = str(uuid.uuid4())
    now = _now_iso()

    with neo4j_driver.session() as session:
        result = session.execute_write(
            _register_tx, agent_id, token, name, source_type, description, now
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
) -> Dict[str, Any]:
    # MERGE by name so re-registration returns the existing agent + token
    result = tx.run(
        "MERGE (a:Agent {name: $name}) "
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


def list_agents() -> list[Dict[str, Any]]:
    with neo4j_driver.session() as session:
        return session.execute_read(_list_agents_tx)


def _list_agents_tx(tx: ManagedTransaction) -> list[Dict[str, Any]]:
    result = tx.run("MATCH (a:Agent) RETURN a ORDER BY a.registered_at DESC")
    return [dict(record["a"]) for record in result]


def ensure_agent_indexes() -> None:
    with neo4j_driver.session() as session:
        session.run(
            "CREATE CONSTRAINT agent_token_unique IF NOT EXISTS "
            "FOR (a:Agent) REQUIRE a.token IS UNIQUE"
        )
        session.run(
            "CREATE CONSTRAINT agent_name_unique IF NOT EXISTS "
            "FOR (a:Agent) REQUIRE a.name IS UNIQUE"
        )
    log.info("Agent indexes ensured")
