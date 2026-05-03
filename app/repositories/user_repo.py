from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.repositories.neo4j_connection import neo4j_driver


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_user_indexes() -> None:
    with neo4j_driver.session() as session:
        session.run(
            "CREATE CONSTRAINT user_email_unique IF NOT EXISTS "
            "FOR (u:User) REQUIRE u.email IS UNIQUE"
        )
        session.run(
            "CREATE CONSTRAINT user_username_unique IF NOT EXISTS "
            "FOR (u:User) REQUIRE u.username IS UNIQUE"
        )


def create_user(email: str, username: str, password_hash: str) -> Dict[str, Any]:
    user_id = uuid.uuid4().hex
    now = _now_iso()
    with neo4j_driver.session() as session:
        session.run(
            "CREATE (u:User {"
            "  user_id: $user_id,"
            "  email: $email,"
            "  username: $username,"
            "  password_hash: $password_hash,"
            "  is_active: true,"
            "  created_at: $now,"
            "  updated_at: $now"
            "})",
            user_id=user_id,
            email=email,
            username=username,
            password_hash=password_hash,
            now=now,
        )
    return {
        "user_id": user_id,
        "email": email,
        "username": username,
        "is_active": True,
        "created_at": now,
    }


def get_by_email(email: str) -> Optional[Dict[str, Any]]:
    with neo4j_driver.session() as session:
        result = session.run(
            "MATCH (u:User {email: $email}) RETURN u",
            email=email,
        )
        record = result.single()
        if record is None:
            return None
        return dict(record["u"])


def get_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    with neo4j_driver.session() as session:
        result = session.run(
            "MATCH (u:User {user_id: $user_id}) RETURN u",
            user_id=user_id,
        )
        record = result.single()
        if record is None:
            return None
        return dict(record["u"])
