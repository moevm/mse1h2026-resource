import { useState, useCallback, useRef } from "react";
import { useDrop } from "react-dnd";
import { NODE_TYPES, NODE_BASE_FIELDS } from "../../types/mapper";
import { useMapperStore } from "../../store/mapperStore";
import type { FieldMapping } from "../../types/mapper";

const NODE_TYPE_FIELDS: Record<string, { name: string; type: string; required?: boolean; description?: string }[]> = {
  Service: [
    { name: "language", type: "string" },
    { name: "framework", type: "string" },
    { name: "version", type: "string" },
    { name: "repository_url", type: "string" },
    { name: "tier", type: "int" },
    { name: "rps", type: "float" },
    { name: "latency_p99_ms", type: "float" },
    { name: "error_rate_percent", type: "float" },
  ],
  Database: [
    { name: "engine", type: "string" },
    { name: "version", type: "string" },
    { name: "capacity_gb", type: "float" },
    { name: "region", type: "string" },
    { name: "instance_class", type: "string" },
    { name: "multi_az", type: "boolean" },
  ],
  Pod: [
    { name: "namespace", type: "string" },
    { name: "node_name", type: "string" },
    { name: "ip_address", type: "string" },
    { name: "phase", type: "string" },
    { name: "restart_count", type: "int" },
  ],
  Deployment: [
    { name: "namespace", type: "string" },
    { name: "replicas_desired", type: "int" },
    { name: "replicas_ready", type: "int" },
    { name: "strategy", type: "string" },
  ],
  Cache: [
    { name: "engine", type: "string" },
    { name: "eviction_policy", type: "string" },
    { name: "max_memory_mb", type: "int" },
    { name: "hit_rate", type: "float" },
  ],
  QueueTopic: [
    { name: "broker", type: "string" },
    { name: "partitions", type: "int" },
    { name: "consumer_lag", type: "int" },
    { name: "message_rate", type: "float" },
  ],
  Endpoint: [
    { name: "path", type: "string" },
    { name: "method", type: "string" },
    { name: "rps_limit", type: "float" },
    { name: "timeout_ms", type: "int" },
  ],
};

interface DragItem {
  type: "FIELD";
  path: string;
  value: unknown;
  dataType: string;
}

function DroppableFieldRow({
  nodeType,
  field,
  mappingInfo,
  onDrop,
}: {
  nodeType: string;
  field: { name: string; type: string; required?: boolean; description?: string };
  mappingInfo: { mapping: FieldMapping } | null;
  onDrop: (nodeType: string, fieldName: string, item: DragItem) => void;
}) {
  const ref = useRef<HTMLTableRowElement>(null);

  const [{ isOver, canDrop }, drop] = useDrop<DragItem, unknown, { isOver: boolean; canDrop: boolean }>(() => ({
    accept: "FIELD",
    drop: (item) => onDrop(nodeType, field.name, item),
    collect: (monitor) => ({
      isOver: monitor.isOver(),
      canDrop: monitor.canDrop(),
    }),
  }), [nodeType, field.name, onDrop]);

  drop(ref);

  const hasMapping = mappingInfo !== null;

  const getBgColor = () => {
    if (isOver && canDrop) return "bg-emerald-500/20 border-emerald-500/50";
    if (canDrop) return "bg-blue-500/10 border-blue-500/30";
    if (hasMapping) return "bg-emerald-500/10";
    return "";
  };

  return (
    <tr
      ref={ref}
      className={`border-b border-slate-700/30 transition-colors cursor-pointer ${getBgColor()}`}
    >
      <td className="py-1.5 pr-2">
        <span className={`font-mono text-sm ${hasMapping ? "text-emerald-400" : "text-blue-400"}`}>
          {field.name}
        </span>
        {hasMapping && <span className="ml-1.5 text-emerald-500">✓</span>}
      </td>
      <td className="py-1.5 text-slate-500 text-sm">{field.type}</td>
      <td className="py-1.5 text-center">
        {field.required && <span className="text-red-400 text-xs">*</span>}
      </td>
      <td className="py-1.5 text-xs">
        {hasMapping && (
          <span className="text-orange-400 font-mono">
            ← {mappingInfo!.mapping.source_path}
          </span>
        )}
      </td>
    </tr>
  );
}

export function SchemaBrowser() {
  const { activeNodeTypes, toggleActiveNodeType, draftMapping, addFieldMapping } = useMapperStore();
  const [searchQuery, setSearchQuery] = useState("");

  const filteredTypes = NODE_TYPES.filter((type) =>
    type.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getMappingInfo = useCallback((nodeType: string, fieldName: string): { mapping: FieldMapping } | null => {
    const mappings = draftMapping?.field_mappings || [];
    const mapping = mappings.find((m) => m.target_node_type === nodeType && m.target_field === fieldName);
    return mapping ? { mapping } : null;
  }, [draftMapping?.field_mappings]);

  const getMappedFields = useCallback((nodeType: string): Set<string> => {
    const mappings = draftMapping?.field_mappings || [];
    return new Set(
      mappings.filter((m) => m.target_node_type === nodeType).map((m) => m.target_field)
    );
  }, [draftMapping?.field_mappings]);

  const handleDrop = useCallback((nodeType: string, fieldName: string, item: DragItem) => {
    const mapping: FieldMapping = {
      id: `fm-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      source_path: item.path,
      target_field: fieldName,
      target_node_type: nodeType,
      transform_type: "direct",
      transform_config: {},
      is_required: false,
      default_value: null,
      description: null,
    };
    addFieldMapping(mapping);
  }, [addFieldMapping]);

  return (
    <div className="h-full flex flex-col p-2">
      
      <div className="mb-2 shrink-0">
        <input
          type="text"
          placeholder="Search node types..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full px-3 py-1.5 bg-slate-800 border border-slate-700 rounded text-sm text-slate-200 placeholder:text-slate-500"
        />
      </div>

      
      <div className="flex-1 overflow-y-auto space-y-1 min-h-0">
        {filteredTypes.map((nodeType) => {
          const isActive = activeNodeTypes.has(nodeType);
          const specificFields = NODE_TYPE_FIELDS[nodeType] || [];
          const allFields = [...NODE_BASE_FIELDS, ...specificFields];
          const mappedFields = getMappedFields(nodeType);
          const mappedCount = mappedFields.size;

          return (
            <div key={nodeType} className="border border-slate-700/50 rounded-lg overflow-hidden">
              <div
                className={`px-3 py-2 cursor-pointer flex items-center justify-between transition-colors ${
                  isActive ? "bg-slate-800" : "bg-slate-800/50 hover:bg-slate-800"
                }`}
                onClick={() => toggleActiveNodeType(nodeType)}
              >
                <div className="flex items-center gap-2">
                  <span className={`text-xs transition-transform ${isActive ? "rotate-90" : ""}`}>▶</span>
                  <span className="font-medium text-sm text-slate-200">{nodeType}</span>
                </div>
                <div className="flex items-center gap-2">
                  {mappedCount > 0 && (
                    <span className="text-xs bg-emerald-500/20 text-emerald-400 px-1.5 py-0.5 rounded">
                      {mappedCount} mapped
                    </span>
                  )}
                  <span className="text-xs text-slate-500">{allFields.length} fields</span>
                </div>
              </div>
              {isActive && (
                <div className="text-xs bg-slate-800/30 max-h-48 overflow-y-auto overflow-x-hidden">
                  <table className="w-full">
                    <thead>
                      <tr className="text-slate-500 border-b border-slate-700/50 sticky top-0 bg-slate-900">
                        <th className="text-left py-1 font-normal px-2">Field</th>
                        <th className="text-left py-1 font-normal">Type</th>
                        <th className="text-center py-1 font-normal w-8">Req</th>
                        <th className="text-left py-1 font-normal">Source</th>
                      </tr>
                    </thead>
                    <tbody>
                      {allFields.map((field) => (
                        <DroppableFieldRow
                          key={field.name}
                          nodeType={nodeType}
                          field={field}
                          mappingInfo={getMappingInfo(nodeType, field.name)}
                          onDrop={handleDrop}
                        />
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
