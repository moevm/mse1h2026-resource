from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from neo4j import Session

from app.models.mapper.mapping import MappingConfig, FieldMapping, ConditionalRule, AutoEdgeRule, MappingListResponse
from app.repositories.neo4j_connection import neo4j_driver


class MappingRepository:
    """Repository for storing and retrieving mapping configurations in Neo4j."""

    @staticmethod
    def _dump_model_or_dict(item: Any) -> Dict[str, Any]:
        """Serialize an item that may be a Pydantic model or plain dict."""
        if hasattr(item, "model_dump"):
            return item.model_dump()
        if isinstance(item, dict):
            return item
        raise TypeError(f"Unsupported mapping item type: {type(item).__name__}")

    def _serialize_mapping(self, mapping: MappingConfig) -> Dict[str, Any]:
        """Convert MappingConfig to Neo4j-compatible dict."""
        return {
            "id": mapping.id,
            "name": mapping.name,
            "source_type": mapping.source_type,
            "version": mapping.version,
            "is_active": mapping.is_active,
            "created_at": mapping.created_at.isoformat(),
            "updated_at": mapping.updated_at.isoformat(),
            "created_by": mapping.created_by,
            "description": mapping.description,
            "sample_chunk_id": mapping.sample_chunk_id,
            "field_mappings": json.dumps([
                self._dump_model_or_dict(fm) for fm in mapping.field_mappings
            ]),
            "conditional_rules": json.dumps([
                self._dump_model_or_dict(cr) for cr in mapping.conditional_rules
            ]),
            "auto_edge_rules": json.dumps([
                self._dump_model_or_dict(r) for r in mapping.auto_edge_rules
            ]) if mapping.auto_edge_rules else "[]",
            "edge_preset_id": mapping.edge_preset_id,
            "edge_source_path": mapping.edge_source_path,
            "edge_target_path": mapping.edge_target_path,
            "edge_type_path": mapping.edge_type_path,
            "edge_type_default": mapping.edge_type_default,
        }

    def _deserialize_mapping(self, data: Dict[str, Any]) -> MappingConfig:
        """Convert Neo4j result to MappingConfig."""
        field_mappings = [
            FieldMapping(**fm) for fm in json.loads(data.get("field_mappings", "[]"))
        ]
        conditional_rules = [
            ConditionalRule(**cr) for cr in json.loads(data.get("conditional_rules", "[]"))
        ]
        auto_edge_rules = [
            AutoEdgeRule(**r) for r in json.loads(data.get("auto_edge_rules", "[]"))
        ]

        return MappingConfig(
            id=data["id"],
            name=data["name"],
            source_type=data["source_type"],
            version=data.get("version", "1.0.0"),
            is_active=data.get("is_active", True),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.utcnow(),
            created_by=data.get("created_by", "system"),
            description=data.get("description"),
            sample_chunk_id=data.get("sample_chunk_id"),
            field_mappings=field_mappings,
            conditional_rules=conditional_rules,
            auto_edge_rules=auto_edge_rules,
            edge_preset_id=data.get("edge_preset_id"),
            edge_source_path=data.get("edge_source_path"),
            edge_target_path=data.get("edge_target_path"),
            edge_type_path=data.get("edge_type_path"),
            edge_type_default=data.get("edge_type_default"),
        )

    def ensure_indexes(self) -> None:
        """Create indexes for MappingConfig nodes."""
        with neo4j_driver.driver.session() as session:
            session.run(
                "CREATE CONSTRAINT mapping_id_unique IF NOT EXISTS "
                "FOR (m:MappingConfig) REQUIRE m.id IS UNIQUE"
            )
            session.run(
                "CREATE INDEX mapping_source_type_idx IF NOT EXISTS "
                "FOR (m:MappingConfig) ON (m.source_type)"
            )
            session.run(
                "CREATE INDEX mapping_active_idx IF NOT EXISTS "
                "FOR (m:MappingConfig) ON (m.is_active)"
            )

    def create(self, mapping: MappingConfig) -> MappingConfig:
        """Create a new mapping configuration."""
        if not mapping.id:
            mapping.id = str(uuid.uuid4())
        mapping.created_at = datetime.utcnow()
        mapping.updated_at = mapping.created_at

        data = self._serialize_mapping(mapping)

        with neo4j_driver.driver.session() as session:
            session.run(
                """
                CREATE (m:MappingConfig $props)
                """,
                props=data,
            )
        return mapping

    def get(self, mapping_id: str) -> Optional[MappingConfig]:
        """Get a mapping configuration by ID."""
        with neo4j_driver.driver.session() as session:
            result = session.run(
                "MATCH (m:MappingConfig {id: $id}) RETURN m",
                id=mapping_id,
            )
            record = result.single()
            if record:
                return self._deserialize_mapping(dict(record["m"]))
        return None

    def get_by_name(self, name: str) -> Optional[MappingConfig]:
        """Get a mapping configuration by name."""
        with neo4j_driver.driver.session() as session:
            result = session.run(
                "MATCH (m:MappingConfig {name: $name}) RETURN m",
                name=name,
            )
            record = result.single()
            if record:
                return self._deserialize_mapping(dict(record["m"]))
        return None

    def list(
        self,
        source_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 100,
    ) -> MappingListResponse:
        """List mapping configurations with optional filters."""
        conditions = []
        params: Dict[str, Any] = {"limit": limit}

        if source_type:
            conditions.append("m.source_type = $source_type")
            params["source_type"] = source_type

        if is_active is not None:
            conditions.append("m.is_active = $is_active")
            params["is_active"] = is_active

        where_clause = " AND ".join(conditions) if conditions else "true"

        with neo4j_driver.driver.session() as session:
            result = session.run(
                f"""
                MATCH (m:MappingConfig)
                WHERE {where_clause}
                RETURN m
                ORDER BY m.updated_at DESC
                LIMIT $limit
                """,
                **params,
            )
            mappings = [self._deserialize_mapping(dict(record["m"])) for record in result]

            # Get total count
            count_result = session.run(
                f"""
                MATCH (m:MappingConfig)
                WHERE {where_clause}
                RETURN count(m) as total
                """,
                **{k: v for k, v in params.items() if k != "limit"},
            )
            count_record = count_result.single()
            total = count_record["total"] if count_record else 0

        return MappingListResponse(mappings=mappings, total=total)

    def update(self, mapping_id: str, mapping: MappingConfig) -> Optional[MappingConfig]:
        """Update a mapping configuration."""
        mapping.updated_at = datetime.utcnow()
        data = self._serialize_mapping(mapping)

        with neo4j_driver.driver.session() as session:
            result = session.run(
                """
                MATCH (m:MappingConfig {id: $id})
                SET m += $props
                RETURN m
                """,
                id=mapping_id,
                props=data,
            )
            record = result.single()
            if record:
                return self._deserialize_mapping(dict(record["m"]))
        return None

    def delete(self, mapping_id: str) -> bool:
        """Delete a mapping configuration."""
        with neo4j_driver.driver.session() as session:
            result = session.run(
                "MATCH (m:MappingConfig {id: $id}) DELETE m RETURN count(m) as deleted",
                id=mapping_id,
            )
            record = result.single()
            return record and record["deleted"] > 0

    def set_active(self, mapping_id: str, is_active: bool) -> Optional[MappingConfig]:
        """Activate or deactivate a mapping."""
        with neo4j_driver.driver.session() as session:
            result = session.run(
                """
                MATCH (m:MappingConfig {id: $id})
                SET m.is_active = $is_active, m.updated_at = $updated_at
                RETURN m
                """,
                id=mapping_id,
                is_active=is_active,
                updated_at=datetime.utcnow().isoformat(),
            )
            record = result.single()
            if record:
                return self._deserialize_mapping(dict(record["m"]))
        return None

    def get_active_for_source(self, source_type: str) -> Optional[MappingConfig]:
        """Get the active mapping for a specific source type."""
        with neo4j_driver.driver.session() as session:
            result = session.run(
                """
                MATCH (m:MappingConfig {source_type: $source_type, is_active: true})
                RETURN m
                ORDER BY m.updated_at DESC
                LIMIT 1
                """,
                source_type=source_type,
            )
            record = result.single()
            if record:
                return self._deserialize_mapping(dict(record["m"]))
        return None

    def deactivate_all_for_source(self, source_type: str) -> int:
        """Deactivate all mappings for a source type.

        Used when activating a new mapping to ensure only one is active.
        """
        with neo4j_driver.driver.session() as session:
            result = session.run(
                """
                MATCH (m:MappingConfig {source_type: $source_type})
                WHERE m.is_active = true
                SET m.is_active = false, m.updated_at = $updated_at
                RETURN count(m) as deactivated
                """,
                source_type=source_type,
                updated_at=datetime.utcnow().isoformat(),
            )
            record = result.single()
            return record["deactivated"] if record else 0

    def activate_for_source(self, mapping_id: str) -> Optional[MappingConfig]:
        """Activate a mapping and deactivate others with same source_type.

        Ensures only one mapping is active per source type.
        """
        mapping = self.get(mapping_id)
        if not mapping:
            return None

        # Deactivate others
        self.deactivate_all_for_source(mapping.source_type)

        # Activate this one
        return self.set_active(mapping_id, True)


mapping_repo = MappingRepository()