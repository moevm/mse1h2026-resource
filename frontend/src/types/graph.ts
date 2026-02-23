export interface GraphNode {
    id: string;
    type: string;
    name: string;
    status?: string;
    environment?: string;
    properties: Record<string, unknown>;
}

export interface GraphEdge {
    source_id: string;
    target_id: string;
    type: string;
    status?: string;
    properties: Record<string, unknown>;
}

export interface GraphResponse {
    nodes: GraphNode[];
    edges: GraphEdge[];
    node_count: number;
    edge_count: number;
}

export interface LayoutNode extends GraphNode {
    x: number;
    y: number;
}

export interface LayoutGraphResponse {
    nodes: LayoutNode[];
    edges: GraphEdge[];
    node_count: number;
    edge_count: number;
    layout: string;
}

export interface GraphStats {
    total_nodes: number;
    total_edges: number;
    nodes_by_type: Record<string, number>;
    edges_by_type: Record<string, number>;
}

export interface GraphAnalytics {
    pagerank: Record<string, number>;
    betweenness: Record<string, number>;
    in_degree: Record<string, number>;
    out_degree: Record<string, number>;
    communities: string[][];
}

export interface SubgraphRequest {
    center_node_id: string;
    depth: number;
    node_types?: string[];
    edge_types?: string[];
}

export interface PathRequest {
    source_id: string;
    target_id: string;
    max_depth?: number;
}

export interface ImpactRequest {
    node_id: string;
    depth?: number;
    direction?: "upstream" | "downstream" | "both";
}

export interface HealthResponse {
    status: string;
}

export interface IngestTopologyRequest {
    source: string;
    timestamp: string;
    nodes: IngestNode[];
    edges: IngestEdge[];
}

export interface IngestNode {
    id: string;
    type: string;
    name: string;
    [key: string]: unknown;
}

export interface IngestEdge {
    source_id: string;
    target_id: string;
    type: string;
    [key: string]: unknown;
}

export interface IngestResult {
    nodes_processed: number;
    edges_processed: number;
    errors: string[];
    success: boolean;
}

export type LogLevel = "info" | "warn" | "error" | "success";

export interface LogEntry {
    id: string;
    timestamp: string;
    level: LogLevel;
    source: string;
    message: string;
    details?: Record<string, unknown>;
}

export interface ServiceProperties {
    language?: string;
    framework?: string;
    version?: string;
    repository_url?: string;
    tier?: number;
    is_external?: boolean;
    memory_allocated_mb?: number;
    cpu_allocated_cores?: number;
}

export interface DeploymentProperties {
    replicas_desired?: number;
    replicas_ready?: number;
    strategy?: string;
    namespace?: string;
    image_tag?: string;
}

export interface PodProperties {
    phase?: string;
    restart_count?: number;
    cpu_usage_m?: number;
    memory_usage_mi?: number;
    namespace?: string;
    node_name?: string;
}

export interface DatabaseProperties {
    engine?: string;
    version?: string;
    capacity_gb?: number;
    is_managed?: boolean;
    region?: string;
    max_connections?: number;
    multi_az?: boolean;
}

export interface CacheProperties {
    engine?: string;
    eviction_policy?: string;
    max_memory_mb?: number;
    hit_rate_target?: number;
    keys_count?: number;
    connected_clients?: number;
}

export interface QueueTopicProperties {
    broker?: string;
    partitions?: number;
    message_rate?: number;
    replication_factor?: number;
}

export interface CallsEdgeProperties {
    protocol?: string;
    rps?: number;
    latency_p99_ms?: number;
    error_rate_percent?: number;
    timeout_ms?: number;
    circuit_breaker_enabled?: boolean;
}

export interface DependsOnEdgeProperties {
    criticality?: string;
    fallback_available?: boolean;
    circuit_breaker_state?: string;
    impact_score?: number;
}

export interface ExportFormatInfo {
    format: ExportFormat;
    description: string;
    content_type: string;
    extension: string;
}

export type ExportFormat = "json" | "graphml" | "gexf" | "dot" | "cytoscape_json" | "csv";

export interface ExportRequest {
    format: ExportFormat;
    limit?: number;
    node_types?: string[];
    edge_types?: string[];
    include_properties?: boolean;
    layout?: string;
}

export interface TraversalStep {
    edge_types: string[];
    direction: "outgoing" | "incoming" | "any";
    target_node_types?: string[];
    min_depth?: number;
    max_depth?: number;
}

export interface TraversalRule {
    name: string;
    description?: string;
    start_node_id?: string;
    start_node_types?: string[];
    steps: TraversalStep[];
    limit?: number;
}

export interface TraversalPreset extends TraversalRule {
    description: string;
}
