// Raw Data Types
export type RawDataSource =
  | "opentelemetry-traces"
  | "opentelemetry-metrics"
  | "istio-metrics"
  | "istio-access-logs"
  | "kubernetes-api"
  | "prometheus"
  | "terraform-state"
  | "argocd"
  | "api-gateway"
  | "custom";

export interface RawDataChunk {
  id: string;
  agent_id: string;
  source_type: RawDataSource;
  timestamp: string;
  sequence: number;
  data: Record<string, unknown>;
  metadata: Record<string, unknown>;
  size_bytes: number;
  is_processed: boolean;
  processed_at: string | null;
  mapping_id: string | null;
}

export interface RawDataListResponse {
  chunks: RawDataChunk[];
  total: number;
  timeline_min: string | null;
  timeline_max: string | null;
}

// Mapping Types
export type TransformType = "direct" | "template" | "conditional" | "expression" | "lookup";

export interface FieldMapping {
  id: string;
  source_path: string;
  target_field: string;
  target_node_type: string;
  transform_type: TransformType;
  transform_config: Record<string, unknown>;
  is_required: boolean;
  default_value: unknown;
  description: string | null;
}

export interface ConditionalRule {
  id: string;
  condition: string;
  target_node_type: string;
  field_mappings: string[];
  priority: number;
}

export interface AutoEdgeRule {
  id: string;
  source_type: string;
  source_field: string;
  target_type: string;
  target_field: string;
  edge_type: string;
}

export interface UnresolvedReference {
  source_node_id: string;
  source_node_type: string;
  source_field: string;
  expected_target_type: string;
  expected_target_value: string;
  rule_id: string;
}

export interface MappingConfig {
  id: string;
  name: string;
  source_type: string;
  version: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  created_by: string;
  description: string | null;
  sample_chunk_id: string | null;
  field_mappings: FieldMapping[];
  conditional_rules: ConditionalRule[];
  auto_edge_rules: AutoEdgeRule[];
  edge_preset_id: string | null;
  // Legacy edge mapping (deprecated)
  edge_source_path: string | null;
  edge_target_path: string | null;
  edge_type_path: string | null;
  edge_type_default: string | null;
}

// Edge Preset Types
export interface EdgePreset {
  id: string;
  name: string;
  description: string | null;
  rules: AutoEdgeRule[];
  is_builtin: boolean;
  created_at: string;
  updated_at: string;
  created_by: string;
}

export interface EdgePresetCreate {
  name: string;
  description?: string;
  rules: AutoEdgeRule[];
}

export interface EdgePresetUpdate {
  name?: string;
  description?: string;
  rules?: AutoEdgeRule[];
}

export interface EdgePresetListResponse {
  presets: EdgePreset[];
  total: number;
}

export interface MappingListResponse {
  mappings: MappingConfig[];
  total: number;
}

// Preview Types
export interface PreviewRequest {
  chunk_id: string;
  mapping_id: string;
}

export interface PreviewResponse {
  chunk_id: string;
  mapping_id: string;
  nodes: Record<string, unknown>[];
  edges: Record<string, unknown>[];
  warnings: string[];
  unresolved_references: UnresolvedReference[];
}

export interface ApplyResponse {
  chunk_id: string;
  mapping_id: string;
  nodes_processed: number;
  edges_processed: number;
  success: boolean;
  errors: string[];
  unresolved_references: UnresolvedReference[];
}

export interface MockerCommandResponse {
  command: string;
  success: boolean;
  exit_code: number;
  summary: string;
  stdout: string;
  stderr: string;
}

// Schema Types (for SchemaBrowser)
export interface SchemaField {
  name: string;
  type: string;
  required: boolean;
  description?: string;
}

export interface NodeTypeSchema {
  type: string;
  fields: SchemaField[];
}

// Node types for schema browser
export const NODE_TYPES: string[] = [
  "Service",
  "Endpoint",
  "Deployment",
  "Pod",
  "Node",
  "Database",
  "Table",
  "QueueTopic",
  "Cache",
  "ExternalAPI",
  "SecretConfig",
  "Library",
  "TeamOwner",
  "SLASLO",
  "RegionCluster",
];

// Common fields for all nodes
export const NODE_BASE_FIELDS: SchemaField[] = [
  { name: "id", type: "string", required: true, description: "URN identifier" },
  { name: "name", type: "string", required: true, description: "Human-readable name" },
  { name: "type", type: "string", required: true, description: "Node type" },
  { name: "status", type: "string", required: false, description: "active/inactive/degraded/offline" },
  { name: "environment", type: "string", required: false, description: "Deployment environment" },
  { name: "description", type: "string", required: false },
  { name: "tags", type: "object", required: false, description: "Key-value labels" },
];
