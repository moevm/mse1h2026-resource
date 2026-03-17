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
    """Service for transforming raw data into graph nodes and edges."""

    def map_chunk(
        self,
        chunk: RawDataChunk,
        mapping: MappingConfig,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[UnresolvedReference]]:
        """Transform a raw data chunk into nodes and edges.

        Args:
            chunk: The raw data chunk to transform
            mapping: The mapping configuration to apply

        Returns:
            Tuple of (nodes, edges, unresolved_references)
        """
        raw_data = chunk.data
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []
        unresolved: List[UnresolvedReference] = []

        # Determine which conditional rules apply
        applicable_rules = self._evaluate_conditional_rules(raw_data, mapping.conditional_rules)

        # Group field mappings by target node type
        mappings_by_type = self._group_mappings_by_type(mapping.field_mappings)

        if applicable_rules:
            # Use conditional rules to create multiple node types
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
            # No conditional rules - try to infer node type or use all mappings
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

        # Legacy edge mapping (if configured)
        if mapping.edge_source_path and mapping.edge_target_path:
            edge = self._map_to_edge(raw_data, mapping)
            if edge:
                edges.append(edge)

        # Automatic edge creation based on preset + custom rules
        edge_rules = self._get_edge_rules(mapping)
        auto_edges, auto_unresolved = self._auto_create_edges(nodes, edge_rules)
        edges.extend(auto_edges)
        unresolved.extend(auto_unresolved)

        return nodes, edges, unresolved

    def _get_edge_rules(self, mapping: MappingConfig) -> List[AutoEdgeRule]:
        """Get edge rules from preset + custom rules."""
        rules: List[AutoEdgeRule] = []

        # Load rules from preset
        preset_id = mapping.edge_preset_id or "default"
        preset_rules = edge_preset_repo.get_rules(preset_id)
        rules.extend(preset_rules)

        # Add custom rules from mapping
        rules.extend(mapping.auto_edge_rules)

        return rules

    def _evaluate_conditional_rules(
        self,
        raw_data: Dict[str, Any],
        rules: List[ConditionalRule],
    ) -> List[ConditionalRule]:
        """Evaluate conditional rules and return matching ones sorted by priority."""
        matching = []
        for rule in rules:
            if transform_service.evaluate_condition(raw_data, rule.condition):
                matching.append(rule)

        # Sort by priority (highest first)
        matching.sort(key=lambda r: r.priority, reverse=True)
        return matching

    def _group_mappings_by_type(
        self,
        mappings: List[FieldMapping],
    ) -> Dict[str, List[FieldMapping]]:
        """Group field mappings by their target node type."""
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
        """Map raw data to a specific node type.

        Args:
            raw_data: The raw source data
            node_type: Target node type (Service, Database, etc.)
            field_mappings: Field mappings for this node type
            mapping_config: Full mapping configuration for context

        Returns:
            Node dictionary or None if required fields missing
        """
        node: Dict[str, Any] = {"type": node_type}
        context = {"source_data": raw_data, "node_type": node_type}

        for field_mapping in field_mappings:
            if field_mapping.target_node_type != node_type:
                continue

            # Extract value using JMESPath
            value = transform_service.extract(raw_data, field_mapping.source_path)

            # Apply transformation
            transformed = transform_service.apply_transform(
                value,
                field_mapping,
                context,
            )

            if transformed is not None:
                node[field_mapping.target_field] = transformed
            elif field_mapping.default_value is not None:
                node[field_mapping.target_field] = field_mapping.default_value

        # Ensure required fields are present
        if "id" not in node:
            log.debug(f"Skipping node of type {node_type}: missing id field")
            return None

        # Generate URN if not present
        if not node["id"].startswith("urn:"):
            node["id"] = f"urn:{node_type.lower()}:{node['id']}"

        # Ensure name field
        if "name" not in node:
            node["name"] = node.get("id", "").split(":")[-1]

        # Add metadata
        node.setdefault("status", "active")

        return node

    def _map_to_edge(
        self,
        raw_data: Dict[str, Any],
        mapping: MappingConfig,
    ) -> Optional[Dict[str, Any]]:
        """Map raw data to an edge.

        Args:
            raw_data: The raw source data
            mapping: Full mapping configuration

        Returns:
            Edge dictionary or None if required fields missing
        """
        from app.repositories.neo4j_repo import find_node_by_name

        if not mapping.edge_source_path or not mapping.edge_target_path:
            return None

        source_id = transform_service.extract(raw_data, mapping.edge_source_path)
        target_id = transform_service.extract(raw_data, mapping.edge_target_path)
        edge_type = transform_service.extract(raw_data, mapping.edge_type_path)

        if not source_id or not target_id:
            log.debug("Skipping edge: missing source_id or target_id")
            return None

        # Resolve URN format by looking up nodes in Neo4j
        if not str(source_id).startswith("urn:"):
            source_node = find_node_by_name(str(source_id))
            if source_node:
                source_id = source_node["id"]  # Already has correct URN
            else:
                # Fallback - use generic resource URN
                source_id = f"urn:resource:{source_id}"

        if not str(target_id).startswith("urn:"):
            target_node = find_node_by_name(str(target_id))
            if target_node:
                target_id = target_node["id"]  # Already has correct URN
            else:
                # Fallback - use generic resource URN
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
        """Automatically create edges based on node field values.

        For each node, check if any auto-edge rules apply and create
        edges to existing target nodes in the graph.

        Args:
            nodes: List of mapped nodes
            rules: Auto-edge rules to apply (builtin + custom)

        Returns:
            Tuple of (edges, unresolved_references)
        """
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

                # Support arrays: if field is a list, process each element
                values = (
                    source_field_value
                    if isinstance(source_field_value, list)
                    else [source_field_value]
                )

                for value in values:
                    if not value:
                        continue

                    # Find target node in Neo4j
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
                        # Target not found — record as unresolved
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
        """Preview mapping result without persisting.

        Returns:
            Tuple of (nodes, edges, warnings, unresolved_references)
        """
        warnings: List[str] = []

        # Create temporary chunk for mapping
        from app.models.mapper.raw_data import RawDataSource
        temp_chunk = RawDataChunk(
            id="preview",
            agent_id="preview",
            source_type=RawDataSource.CUSTOM,
            data=raw_data,
        )

        nodes, edges, unresolved = self.map_chunk(temp_chunk, mapping)

        # Add warnings for missing required fields
        if not nodes:
            warnings.append("No nodes were generated from the mapping")

        for node in nodes:
            if "id" not in node:
                warnings.append(f"Node missing required 'id' field: {node}")

        # Add warnings for unresolved references
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
        """Infer the most likely node type from data structure.

        This is a heuristic for when no conditional rules match.
        """
        # Check for common patterns
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
            # Check for database span
            attrs = raw_data.get("attributes", {})
            if attrs.get("db.system"):
                return "Database"
            # Check for messaging span
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

        # Default to Service
        return "Service"


mapper_service = MapperService()
