import { useState, useCallback, useEffect } from "react";
import { useMapperStore } from "../../store/mapperStore";
import { mapperApi } from "../../api/mapperApi";
import { NODE_TYPES } from "../../types/mapper";
import type { FieldMapping, TransformType, EdgePreset } from "../../types/mapper";

const TRANSFORM_TYPES: { value: TransformType; label: string }[] = [
  { value: "direct", label: "Direct" },
  { value: "template", label: "Template" },
  { value: "lookup", label: "Lookup" },
  { value: "expression", label: "Expression" },
];

// Mapping card component - compact version
function MappingCard({
  mapping,
  onRemove,
  onUpdate,
}: {
  mapping: FieldMapping;
  onRemove: () => void;
  onUpdate: (updates: Partial<FieldMapping>) => void;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded overflow-hidden text-xs">
      <div className="px-2 py-1.5 flex items-center gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="px-1 py-0.5 bg-blue-500/20 text-blue-400 rounded text-[10px] font-medium">
              {mapping.target_node_type}
            </span>
            <span className="font-mono text-orange-400 truncate">
              {mapping.source_path}
            </span>
          </div>
          <div className="text-slate-400 mt-0.5 flex items-center gap-1">
            <span className="text-slate-600">→</span>
            <span className="font-medium text-emerald-400">{mapping.target_field}</span>
          </div>
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-slate-500 hover:text-slate-300 p-0.5"
        >
          <span className={`text-[10px] transition-transform ${expanded ? "rotate-180" : ""}`}>▼</span>
        </button>
        <button
          onClick={onRemove}
          className="text-red-500/70 hover:text-red-400 p-0.5"
          title="Remove"
        >
          ✕
        </button>
      </div>
      {expanded && (
        <div className="px-2 py-1.5 border-t border-slate-700/50 bg-slate-800/30">
          <div className="grid grid-cols-2 gap-1.5">
            <div>
              <label className="block text-slate-600 mb-0.5 text-[10px]">Transform</label>
              <select
                value={mapping.transform_type}
                onChange={(e) => onUpdate({ transform_type: e.target.value as TransformType })}
                className="w-full px-1.5 py-0.5 bg-slate-700 border border-slate-600 rounded text-slate-200 text-[10px]"
              >
                {TRANSFORM_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-slate-600 mb-0.5 text-[10px]">Default</label>
              <input
                type="text"
                value={(mapping.default_value as string) || ""}
                onChange={(e) => onUpdate({ default_value: e.target.value || null })}
                placeholder="Optional"
                className="w-full px-1.5 py-0.5 bg-slate-700 border border-slate-600 rounded text-slate-200 text-[10px]"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export function MappingBuilder() {
  const {
    draftMapping,
    selectedFieldPath,
    updateDraftMapping,
    addFieldMapping,
    updateFieldMapping,
    removeFieldMapping,
    setSelectedFieldPath,
    saveDraftMapping,
  } = useMapperStore();

  const [newMapping, setNewMapping] = useState<Partial<FieldMapping>>({
    source_path: "",
    target_field: "",
    target_node_type: "Service",
    transform_type: "direct",
  });

  const [saving, setSaving] = useState(false);
  const [edgePresets, setEdgePresets] = useState<EdgePreset[]>([]);
  const [presetsLoading, setPresetsLoading] = useState(false);

  // Load edge presets
  useEffect(() => {
    async function loadPresets() {
      setPresetsLoading(true);
      try {
        const response = await mapperApi.listEdgePresets();
        setEdgePresets(response.presets);
      } catch (error) {
        console.error("Failed to load edge presets:", error);
      } finally {
        setPresetsLoading(false);
      }
    }
    loadPresets();
  }, []);

  const handleAddMapping = useCallback(() => {
    if (!newMapping.source_path || !newMapping.target_field) return;

    const mapping: FieldMapping = {
      id: `fm-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      source_path: newMapping.source_path,
      target_field: newMapping.target_field,
      target_node_type: newMapping.target_node_type || "Service",
      transform_type: newMapping.transform_type || "direct",
      transform_config: {},
      is_required: false,
      default_value: null,
      description: null,
    };

    addFieldMapping(mapping);
    setNewMapping({
      source_path: "",
      target_field: "",
      target_node_type: newMapping.target_node_type || "Service",
      transform_type: "direct",
    });
    setSelectedFieldPath(null);
  }, [newMapping, addFieldMapping, setSelectedFieldPath]);

  // Auto-fill source path from selected field
  const handleSourcePathFocus = useCallback(() => {
    if (selectedFieldPath) {
      setNewMapping((prev) => ({ ...prev, source_path: selectedFieldPath }));
      setSelectedFieldPath(null);
    }
  }, [selectedFieldPath, setSelectedFieldPath]);

  const handleSave = useCallback(async () => {
    if (!draftMapping) return;
    setSaving(true);
    try {
      await saveDraftMapping();
    } finally {
      setSaving(false);
    }
  }, [draftMapping, saveDraftMapping]);

  const fieldMappings = draftMapping?.field_mappings || [];

  // Group mappings by node type
  const mappingsByNodeType = fieldMappings.reduce((acc, mapping) => {
    const type = mapping.target_node_type;
    if (!acc[type]) acc[type] = [];
    acc[type].push(mapping);
    return acc;
  }, {} as Record<string, FieldMapping[]>);

  // Get selected preset info
  const selectedPreset = edgePresets.find(p => p.id === (draftMapping?.edge_preset_id || "default"));

  return (
    <div className="p-3 text-sm">
      {/* Mapping Name - Inline */}
      <div className="flex items-center gap-2 mb-3">
        <input
          type="text"
          value={draftMapping?.name || ""}
          onChange={(e) => updateDraftMapping({ name: e.target.value })}
          className="flex-1 px-2 py-1 bg-slate-800 border border-slate-700 rounded text-sm text-slate-200"
          placeholder="Mapping name..."
        />
        {draftMapping?.id && (
          <button
            onClick={handleSave}
            disabled={saving}
            className="text-xs bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-700 text-white px-2 py-1 rounded"
          >
            {saving ? "..." : "Save"}
          </button>
        )}
      </div>

      {/* Auto Edge Creation - Always visible */}
      <div className="mb-3 p-2 bg-emerald-900/20 border border-emerald-700/30 rounded">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-emerald-400">⚡</span>
            <span className="text-xs font-medium text-emerald-400">Auto Edge Creation</span>
          </div>
          <select
            value={draftMapping?.edge_preset_id || "default"}
            onChange={(e) => updateDraftMapping({ edge_preset_id: e.target.value })}
            disabled={presetsLoading}
            className="px-2 py-0.5 bg-slate-700 border border-slate-600 rounded text-xs text-slate-200"
          >
            {edgePresets.map((preset) => (
              <option key={preset.id} value={preset.id}>
                {preset.name} {preset.is_builtin ? "⭐" : ""}
              </option>
            ))}
          </select>
        </div>
        {selectedPreset && (
          <div className="mt-1.5 text-[10px] text-slate-500">
            {selectedPreset.rules.length} rules • {selectedPreset.is_builtin ? "Built-in" : "Custom"}
          </div>
        )}
      </div>

      {/* Field Mappings List - Compact */}
      <div className="mb-3">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-xs font-medium text-slate-400">
            Mapped Fields ({fieldMappings.length})
          </span>
        </div>

        {fieldMappings.length === 0 ? (
          <div className="text-xs text-slate-500 text-center py-3 bg-slate-800/30 rounded border border-slate-700/50">
            Drag fields from Raw Data to Target Schema
          </div>
        ) : (
          <div className="space-y-1 max-h-32 overflow-auto">
            {Object.entries(mappingsByNodeType).map(([nodeType, mappings]) => (
              <div key={nodeType}>
                <div className="text-[10px] text-slate-600 mb-0.5 flex items-center gap-1">
                  <span className="px-1 py-0.5 bg-blue-500/20 text-blue-400 rounded font-medium">
                    {nodeType}
                  </span>
                  <span>{mappings.length}</span>
                </div>
                <div className="space-y-0.5">
                  {mappings.map((fm) => (
                    <MappingCard
                      key={fm.id}
                      mapping={fm}
                      onRemove={() => removeFieldMapping(fm.id)}
                      onUpdate={(updates) => updateFieldMapping(fm.id, updates)}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quick Add - Inline */}
      <div className="flex items-center gap-1.5">
        <input
          type="text"
          value={newMapping.source_path || ""}
          onChange={(e) => setNewMapping((prev) => ({ ...prev, source_path: e.target.value }))}
          onFocus={handleSourcePathFocus}
          className="flex-1 px-2 py-1 bg-slate-700 border border-slate-600 rounded text-xs text-slate-200"
          placeholder={selectedFieldPath || "source.path"}
        />
        <input
          type="text"
          value={newMapping.target_field || ""}
          onChange={(e) => setNewMapping((prev) => ({ ...prev, target_field: e.target.value }))}
          className="w-20 px-2 py-1 bg-slate-700 border border-slate-600 rounded text-xs text-slate-200"
          placeholder="field"
        />
        <select
          value={newMapping.target_node_type || "Service"}
          onChange={(e) => setNewMapping((prev) => ({ ...prev, target_node_type: e.target.value }))}
          className="px-1.5 py-1 bg-slate-700 border border-slate-600 rounded text-xs text-slate-200"
        >
          {NODE_TYPES.slice(0, 8).map((type) => (
            <option key={type} value={type}>{type}</option>
          ))}
        </select>
        <button
          onClick={handleAddMapping}
          disabled={!newMapping.source_path || !newMapping.target_field}
          className="bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 disabled:text-slate-500 text-white px-2 py-1 rounded text-xs"
        >
          +
        </button>
      </div>
    </div>
  );
}
