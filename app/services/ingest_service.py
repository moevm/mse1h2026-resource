from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from app.models.topology import TopologyUpdate
from app.repositories import neo4j_repo

log = logging.getLogger(__name__)


class IngestResult:
    def __init__(self) -> None:
        self.nodes_processed: int = 0
        self.edges_processed: int = 0
        self.errors: list[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes_processed": self.nodes_processed,
            "edges_processed": self.edges_processed,
            "errors": self.errors,
            "success": len(self.errors) == 0,
        }


def process_topology_update(update: TopologyUpdate) -> IngestResult:
    result = IngestResult()

    node_dicts = [
        n.model_dump(exclude_none=True) for n in update.nodes
    ]
    edge_dicts = [
        e.model_dump(exclude_none=True) for e in update.edges
    ]

    log.info(
        "Ingest from '%s': %d nodes, %d edges",
        update.source,
        len(node_dicts),
        len(edge_dicts),
    )

    try:
        result.nodes_processed = neo4j_repo.upsert_nodes(
            node_dicts, source=update.source,
        )
    except Exception as exc:
        log.exception("Failed to upsert nodes")
        result.errors.append(f"node upsert failed: {exc}")

    try:
        result.edges_processed = neo4j_repo.upsert_edges(
            edge_dicts, source=update.source,
        )
    except Exception as exc:
        log.exception("Failed to upsert edges")
        result.errors.append(f"edge upsert failed: {exc}")

    return result
