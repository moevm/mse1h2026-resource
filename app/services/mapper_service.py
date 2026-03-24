from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.models.mapper.mapping import (
    MappingConfig,
    FieldMapping,
    ConditionalRule,
    AutoEdgeRule,
    UnresolvedReference,
)
from app.models.mapper.raw_data import RawDataChunk
from app.repositories.edge_preset_repo import edge_preset_repo
from app.services.transform_service import transform_service

log = logging.getLogger(__name__)


class MapperService:

    def map_chunk(
        self,
        chunk: RawDataChunk,
        mapping: MappingConfig,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[UnresolvedReference]]:
        raw_data = chunk.data
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []
        unresolved: List[UnresolvedReference] = []

        applicable_rules = self._evaluate_conditional_rules(raw_data, mapping.conditional_rules)

        mappings_by_type = self._group_mappings_by_type(mapping.field_mappings)

        if applicable_rules:
            for rule in applicable_rules:
                node_type = rule.target_node_type
                node = self._map_to_node(
                    raw_data,
                    node_type,
                    mappings_by_type.get(node_type, []),
                    mapping,
                )
                if node:
                    nodes.append(node)
        else:
            node_types = set(mappings_by_type.keys())
            for node_type in node_types:
                node = self._map_to_node(
                    raw_data,
                    node_type,
                    mappings_by_type.get(node_type, []),
                    mapping,
                )
                if node:
                    nodes.append(node)

        if mapping.edge_source_path and mapping.edge_target_path:
            edge = self._map_to_edge(raw_data, mapping)
            if edge:
                edges.append(edge)

        edge_rules = self._get_edge_rules(mapping)
        auto_edges, auto_unresolved = self._auto_create_edges(nodes, edge_rules)
        edges.extend(auto_edges)
        unresolved.extend(auto_unresolved)

        return nodes, edges, unresolved

    def _get_edge_rules(self, mapping: MappingConfig) -> List[AutoEdgeRule]:
        rules: List[AutoEdgeRule] = []

        preset_id = mapping.edge_preset_id or "default"
        preset_rules = edge_preset_repo.get_rules(preset_id)
        rules.extend(preset_rules)

        rules.extend(mapping.auto_edge_rules)

        return rules

    def _evaluate_conditional_rules(
        self,
        raw_data: Dict[str, Any],
        rules: List[ConditionalRule],
    ) -> List[ConditionalRule]:
        matching = []
        for rule in rules:
            if transform_service.evaluate_condition(raw_data, rule.condition):
                matching.append(rule)

        matching.sort(key=lambda r: r.priority, reverse=True)
        return matching

    def _group_mappings_by_type(
        self,
        mappings: List[FieldMapping],
    ) -> Dict[str, List[FieldMapping]]:
        grouped: Dict[str, List[FieldMapping]] = {}
        for mapping in mappings:
            node_type = mapping.target_node_type
            if node_type not in grouped:
                grouped[node_type] = []
            grouped[node_type].append(mapping)
        return grouped

    def _map_to_node(
        self,
        raw_data: Dict[str, Any],
        node_type: str,
        field_mappings: List[FieldMapping],
        mapping_config: MappingConfig,
    ) -> Optional[Dict[str, Any]]:
        node: Dict[str, Any] = {"type": node_type}
        context = {"source_data": raw_data, "node_type": node_type}

        for field_mapping in field_mappings:
            if field_mapping.target_node_type != node_type:
                continue

            value = transform_service.extract(raw_data, field_mapping.source_path)

            transformed = transform_service.apply_transform(
                value,
                field_mapping,
                context,
            )

            if transformed is not None:
                node[field_mapping.target_field] = transformed
            elif field_mapping.default_value is not None:
                node[field_mapping.target_field] = field_mapping.default_value

        if "id" not in node:
            log.debug(f"Skipping node of type {node_type}: missing id field")
            return None

        if not node["id"].startswith("urn:"):
            node["id"] = f"urn:{node_type.lower()}:{node['id']}"

        if "name" not in node:
            node["name"] = node.get("id", "").split(":")[-1]

        node.setdefault("status", "active")

        return node

    def _map_to_edge(
        self,
        raw_data: Dict[str, Any],
        mapping: MappingConfig,
    ) -> Optional[Dict[str, Any]]:
        from app.repositories.neo4j_repo import find_node_by_name

        if not mapping.edge_source_path or not mapping.edge_target_path:
            return None

        source_id = transform_service.extract(raw_data, mapping.edge_source_path)
        target_id = transform_service.extract(raw_data, mapping.edge_target_path)
        edge_type = transform_service.extract(raw_data, mapping.edge_type_path)

        if not source_id or not target_id:
            log.debug("Skipping edge: missing source_id or target_id")
            return None

        if not str(source_id).startswith("urn:"):
            source_node = find_node_by_name(str(source_id))
            if source_node:
                source_id = source_node["id"]  # Already has correct URN
            else:
                source_id = f"urn:resource:{source_id}"

        if not str(target_id).startswith("urn:"):
            target_node = find_node_by_name(str(target_id))
            if target_node:
                target_id = target_node["id"]  # Already has correct URN
            else:
                target_id = f"urn:resource:{target_id}"

        edge = {
            "source_id": str(source_id),
            "target_id": str(target_id),
            "type": edge_type or mapping.edge_type_default or "dependson",
        }

        return edge

    def _auto_create_edges(
        self,
        nodes: List[Dict[str, Any]],
        rules: List[AutoEdgeRule],
    ) -> Tuple[List[Dict[str, Any]], List[UnresolvedReference]]:
        from app.repositories.neo4j_repo import find_node_by_field

        edges: List[Dict[str, Any]] = []
        unresolved: List[UnresolvedReference] = []

        for node in nodes:
            node_type = node.get("type")
            if not node_type:
                continue

            for rule in rules:
                if rule.source_type != node_type:
                    continue

                source_field_value = node.get(rule.source_field)
                if not source_field_value:
                    continue

                values = (
                    source_field_value
                    if isinstance(source_field_value, list)
                    else [source_field_value]
                )

                for value in values:
                    if not value:
                        continue

                    target_node = find_node_by_field(
                        rule.target_type,
                        rule.target_field,
                        str(value),
                    )

                    if target_node:
                        edges.append({
                            "source_id": node["id"],
                            "target_id": target_node["id"],
                            "type": rule.edge_type,
                        })
                    else:
                        unresolved.append(UnresolvedReference(
                            source_node_id=node["id"],
                            source_node_type=node_type,
                            source_field=rule.source_field,
                            expected_target_type=rule.target_type,
                            expected_target_value=str(value),
                            rule_id=rule.id,
                        ))

        return edges, unresolved

    def preview(
        self,
        raw_data: Dict[str, Any],
        mapping: MappingConfig,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str], List[UnresolvedReference]]:
        warnings: List[str] = []

        from app.models.mapper.raw_data import RawDataSource
        temp_chunk = RawDataChunk(
            id="preview",
            agent_id="preview",
            source_type=RawDataSource.CUSTOM,
            data=raw_data,
        )

        nodes, edges, unresolved = self.map_chunk(temp_chunk, mapping)

        if not nodes:
            warnings.append("No nodes were generated from the mapping")

        for node in nodes:
            if "id" not in node:
                warnings.append(f"Node missing required 'id' field: {node}")

        for ref in unresolved:
            warnings.append(
                f"{ref.source_node_type} '{ref.source_node_id.split(':')[-1]}' "
                f"has {ref.source_field}='{ref.expected_target_value}' "
                f"→ {ref.expected_target_type} not found"
            )

        return nodes, edges, warnings, unresolved

    def infer_node_type(
        self,
        raw_data: Dict[str, Any],
        source_type: str,
    ) -> str:
        if source_type == "kubernetes-api":
            kind = raw_data.get("kind", "")
            if kind == "Pod":
                return "Pod"
            elif kind == "Service":
                return "Service"
            elif kind == "Deployment":
                return "Deployment"
            elif kind == "Node":
                return "Node"

        elif source_type == "opentelemetry-traces":
            attrs = raw_data.get("attributes", {})
            if attrs.get("db.system"):
                return "Database"
            if attrs.get("messaging.system"):
                return "QueueTopic"
            return "Service"

        elif source_type == "terraform-state":
            resource_type = raw_data.get("type", "")
            if "db" in resource_type or "rds" in resource_type:
                return "Database"
            elif "cache" in resource_type or "elasticache" in resource_type:
                return "Cache"
            elif "sqs" in resource_type or "sns" in resource_type or "kafka" in resource_type:
                return "QueueTopic"

        return "Service"


mapper_service = MapperService()