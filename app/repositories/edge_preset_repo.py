from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List, Optional

from app.models.mapper.edge_preset import EdgePreset, EdgePresetCreate, EdgePresetUpdate
from app.models.mapper.mapping import AutoEdgeRule
from app.repositories.neo4j_connection import neo4j_driver

log = logging.getLogger(__name__)

# Directory for JSON presets
PRESETS_DIR = Path(__file__).parent.parent.parent / "edge_presets"


class EdgePresetRepository:
    """Repository for edge presets."""

    def __init__(self):
        self._builtin_loaded = False
        self._builtin_presets: List[EdgePreset] = []

    def _load_builtin_presets(self) -> None:
        """Load built-in presets from JSON files."""
        if self._builtin_loaded:
            return

        if PRESETS_DIR.exists():
            for preset_file in PRESETS_DIR.glob("*.json"):
                try:
                    with open(preset_file) as f:
                        data = json.load(f)
                    preset = EdgePreset(
                        id=data.get("id", preset_file.stem),
                        name=data.get("name", preset_file.stem),
                        description=data.get("description"),
                        rules=[AutoEdgeRule(**r) for r in data.get("rules", [])],
                        is_builtin=True,
                    )
                    self._builtin_presets.append(preset)
                    log.info(f"Loaded built-in edge preset: {preset.name}")
                except Exception as e:
                    log.error(f"Failed to load edge preset {preset_file}: {e}")

        self._builtin_loaded = True

    def _parse_rules(self, rules_data) -> List[AutoEdgeRule]:
        """Parse rules from Neo4j (can be JSON string or list)."""
        if not rules_data:
            return []
        if isinstance(rules_data, str):
            rules_list = json.loads(rules_data)
        else:
            rules_list = rules_data
        return [AutoEdgeRule(**r) for r in rules_list]

    def list_all(self) -> List[EdgePreset]:
        """List all presets (built-in + custom from Neo4j)."""
        self._load_builtin_presets()

        # Get custom presets from Neo4j
        custom_presets = self._list_custom()

        return self._builtin_presets + custom_presets

    def _list_custom(self) -> List[EdgePreset]:
        """List custom presets stored in Neo4j."""
        with neo4j_driver.session() as session:
            result = session.run(
                "MATCH (p:EdgePreset) "
                "RETURN p.id AS id, p.name AS name, p.description AS description, "
                "       p.rules AS rules, p.created_at AS created_at, "
                "       p.updated_at AS updated_at, p.created_by AS created_by"
            )
            presets = []
            for record in result:
                rules = self._parse_rules(record.get("rules"))
                presets.append(EdgePreset(
                    id=record["id"],
                    name=record["name"],
                    description=record.get("description"),
                    rules=rules,
                    is_builtin=False,
                    created_at=record.get("created_at"),
                    updated_at=record.get("updated_at"),
                    created_by=record.get("created_by", "system"),
                ))
            return presets

    def get(self, preset_id: str) -> Optional[EdgePreset]:
        """Get a preset by ID."""
        self._load_builtin_presets()

        # Check built-in first
        for preset in self._builtin_presets:
            if preset.id == preset_id:
                return preset

        # Check Neo4j for custom preset
        with neo4j_driver.session() as session:
            result = session.run(
                "MATCH (p:EdgePreset {id: $id}) "
                "RETURN p.id AS id, p.name AS name, p.description AS description, "
                "       p.rules AS rules, p.created_at AS created_at, "
                "       p.updated_at AS updated_at, p.created_by AS created_by",
                id=preset_id,
            )
            record = result.single()
            if not record:
                return None

            rules = self._parse_rules(record.get("rules"))
            return EdgePreset(
                id=record["id"],
                name=record["name"],
                description=record.get("description"),
                rules=rules,
                is_builtin=False,
                created_at=record.get("created_at"),
                updated_at=record.get("updated_at"),
                created_by=record.get("created_by", "system"),
            )

    def create(self, data: EdgePresetCreate, created_by: str = "user") -> EdgePreset:
        """Create a new custom preset."""
        from datetime import datetime
        import json

        preset_id = f"custom-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        now = datetime.utcnow().isoformat()

        # Serialize rules to JSON string for Neo4j storage
        rules_json = json.dumps([r.model_dump() for r in data.rules])

        with neo4j_driver.session() as session:
            session.run(
                "CREATE (p:EdgePreset {"
                "  id: $id, name: $name, description: $description, "
                "  rules: $rules, created_at: $now, updated_at: $now, created_by: $created_by"
                "})",
                id=preset_id,
                name=data.name,
                description=data.description,
                rules=rules_json,
                now=now,
                created_by=created_by,
            )

        return self.get(preset_id)  # type: ignore

    def update(self, preset_id: str, data: EdgePresetUpdate) -> Optional[EdgePreset]:
        """Update a custom preset."""
        preset = self.get(preset_id)
        if not preset:
            return None

        if preset.is_builtin:
            raise ValueError("Cannot modify built-in presets")

        from datetime import datetime
        now = datetime.utcnow().isoformat()

        updates = {}
        if data.name is not None:
            updates["name"] = data.name
        if data.description is not None:
            updates["description"] = data.description
        if data.rules is not None:
            # Serialize rules to JSON string
            updates["rules"] = json.dumps([r.model_dump() for r in data.rules])

        if not updates:
            return preset

        updates["updated_at"] = now

        set_clauses = ", ".join(f"p.{k} = ${k}" for k in updates.keys())
        params = {"id": preset_id, **updates}

        with neo4j_driver.session() as session:
            session.run(
                f"MATCH (p:EdgePreset {{id: $id}}) SET {set_clauses}",
                **params,
            )

        return self.get(preset_id)

    def delete(self, preset_id: str) -> bool:
        """Delete a custom preset."""
        preset = self.get(preset_id)
        if not preset:
            return False

        if preset.is_builtin:
            raise ValueError("Cannot delete built-in presets")

        with neo4j_driver.session() as session:
            result = session.run(
                "MATCH (p:EdgePreset {id: $id}) DELETE p RETURN count(p) AS deleted",
                id=preset_id,
            )
            record = result.single()
            return record["deleted"] > 0 if record else False

    def get_rules(self, preset_id: str) -> List[AutoEdgeRule]:
        """Get rules from a preset by ID. Returns empty list if not found."""
        preset = self.get(preset_id)
        return preset.rules if preset else []


# Singleton instance
edge_preset_repo = EdgePresetRepository()
