from __future__ import annotations

import logging
from neo4j import GraphDatabase, Driver

from app.config import settings

log = logging.getLogger(__name__)


class Neo4jConnection:
    def __init__(self) -> None:
        self._driver: Driver | None = None

    @property
    def driver(self) -> Driver:
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
            )
            log.info("Neo4j driver created → %s", settings.neo4j_uri)
        return self._driver

    def verify_connectivity(self) -> None:
        self.driver.verify_connectivity()
        log.info("Neo4j connectivity verified")

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()
            self._driver = None
            log.info("Neo4j driver closed")

    def ensure_indexes(self) -> None:

        with self.driver.session() as session:
            session.run(
                "CREATE CONSTRAINT resource_ext_id IF NOT EXISTS "
                "FOR (r:Resource) REQUIRE r.external_id IS UNIQUE"
            )
            session.run(
                "CREATE INDEX resource_type_idx IF NOT EXISTS "
                "FOR (r:Resource) ON (r.type)"
            )
            session.run(
                "CREATE INDEX resource_status_idx IF NOT EXISTS "
                "FOR (r:Resource) ON (r.status)"
            )
            log.info("Neo4j indexes / constraints ensured")


    def session(self, **kwargs):
        """Shortcut to open a session with the current driver."""
        return self.driver.session(**kwargs)


neo4j_driver = Neo4jConnection()
