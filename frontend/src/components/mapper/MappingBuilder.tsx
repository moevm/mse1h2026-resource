import { useCallback, useEffect, useState } from 'react';

import { mapperApi } from '../../api/mapperApi';
import { useMapperStore } from '../../store/mapperStore';
import { NODE_TYPES } from '../../types/mapper';
import type { EdgePreset, FieldMapping, TransformType } from '../../types/mapper';

const TRANSFORM_TYPES: { value: TransformType; label: string }[] = [
  { value: 'direct', label: 'Direct' },
  { value: 'template', label: 'Template' },
  { value: 'lookup', label: 'Lookup' },
  { value: 'expression', label: 'Expression' },
];

function MappingCard({
  mapping,
  onRemove,
  onUpdate,
}: Readonly<{
  mapping: FieldMapping;
  onRemove: () => void;
  onUpdate: (updates: Partial<FieldMapping>) => void;
}>) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="overflow-hidden rounded border border-slate-700/50 bg-slate-800/50 text-xs">
      <div className="flex items-center gap-2 px-2 py-1.5">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <span className="rounded bg-blue-500/20 px-1 py-0.5 text-[10px] font-medium text-blue-400">
              {mapping.target_node_type}
            </span>
            <span className="truncate font-mono text-orange-400">{mapping.source_path}</span>
          </div>
          <div className="mt-0.5 flex items-center gap-1 text-slate-400">
            <span className="text-slate-600">→</span>
            <span className="font-medium text-emerald-400">{mapping.target_field}</span>
          </div>
        </div>
        <button onClick={() => setExpanded(!expanded)} className="p-0.5 text-slate-500 hover:text-slate-300">
          <span className={`text-[10px] transition-transform ${expanded ? 'rotate-180' : ''}`}>▼</span>
        </button>
        <button onClick={onRemove} className="p-0.5 text-red-500/70 hover:text-red-400" title="Remove">
          ✕
        </button>
      </div>
      {expanded && (
        <div className="border-t border-slate-700/50 bg-slate-800/30 px-2 py-1.5">
          <div className="grid grid-cols-2 gap-1.5">
            <div>
              <p className="mb-0.5 block text-[10px] text-slate-600">Transform</p>
              <select
                value={mapping.transform_type}
                onChange={(e) => onUpdate({ transform_type: e.target.value as TransformType })}
                className="w-full rounded border border-slate-600 bg-slate-700 px-1.5 py-0.5 text-[10px] text-slate-200"
              >
                {TRANSFORM_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <p className="mb-0.5 block text-[10px] text-slate-600">Default</p>
              <input
                type="text"
                value={(mapping.default_value as string) ?? ''}
                onChange={(e) => onUpdate({ default_value: e.target.value || null })}
                placeholder="Optional"
                className="w-full rounded border border-slate-600 bg-slate-700 px-1.5 py-0.5 text-[10px] text-slate-200"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export function MappingBuilder({ onSaved }: { onSaved?: () => Promise<void> | void }) {
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
    source_path: '',
    target_field: '',
    target_node_type: 'Service',
    transform_type: 'direct',
  });

  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [edgePresets, setEdgePresets] = useState<EdgePreset[]>([]);
  const [presetsLoading, setPresetsLoading] = useState(false);

  useEffect(() => {
    async function loadPresets() {
      setPresetsLoading(true);
      try {
        const response = await mapperApi.listEdgePresets();
        setEdgePresets(response.presets);
      } catch (error) {
        console.error('Failed to load edge presets:', error);
      } finally {
        setPresetsLoading(false);
      }
    }
    void loadPresets();
  }, []);

  const handleAddMapping = useCallback(() => {
    if (!newMapping.source_path || !newMapping.target_field) return;

    const mapping: FieldMapping = {
      id: `fm-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      source_path: newMapping.source_path,
      target_field: newMapping.target_field,
      target_node_type: newMapping.target_node_type ?? 'Service',
      transform_type: newMapping.transform_type ?? 'direct',
      transform_config: {},
      is_required: false,
      default_value: null,
      description: null,
    };

    addFieldMapping(mapping);
    setNewMapping({
      source_path: '',
      target_field: '',
      target_node_type: newMapping.target_node_type ?? 'Service',
      transform_type: 'direct',
    });
    setSelectedFieldPath(null);
  }, [newMapping, addFieldMapping, setSelectedFieldPath]);

  const handleSourcePathFocus = useCallback(() => {
    if (selectedFieldPath) {
      setNewMapping((prev) => ({ ...prev, source_path: selectedFieldPath }));
      setSelectedFieldPath(null);
    }
  }, [selectedFieldPath, setSelectedFieldPath]);

  const handleSave = useCallback(async () => {
    if (!draftMapping) return;
    setSaving(true);
    setSaveError(null);
    try {
      await saveDraftMapping();
      await onSaved?.();
    } catch (error) {
      const detail =
        typeof error === 'object' && error !== null && 'response' in error
          ? (error as { response?: { data?: { detail?: unknown } } }).response?.data?.detail
          : undefined;
      const message = typeof detail === 'string' ? detail : 'Failed to create or save mapping';
      setSaveError(message);
    } finally {
      setSaving(false);
    }
  }, [draftMapping, saveDraftMapping, onSaved]);

  const fieldMappings = draftMapping?.field_mappings ?? [];
  const saveButtonLabel = saving ? '...' : draftMapping?.id ? 'Save' : 'Create';

  const mappingsByNodeType = fieldMappings.reduce(
    (acc, mapping) => {
      const type = mapping.target_node_type;
      if (!acc[type]) acc[type] = [];
      acc[type].push(mapping);
      return acc;
    },
    {} as Record<string, FieldMapping[]>,
  );

  const selectedPreset = edgePresets.find((p) => p.id === (draftMapping?.edge_preset_id ?? 'default'));

  return (
    <div className="flex h-full flex-col p-3 text-sm">
      <div className="mb-3 flex shrink-0 items-center gap-2">
        <input
          type="text"
          value={draftMapping?.name ?? ''}
          onChange={(e) => {
            setSaveError(null);
            updateDraftMapping({ name: e.target.value });
          }}
          className="flex-1 rounded border border-slate-700 bg-slate-800 px-2 py-1 text-sm text-slate-200"
          placeholder="Mapping name..."
        />
        {draftMapping && (
          <button
            onClick={() => {
              void handleSave();
            }}
            disabled={saving || !(draftMapping.name ?? '').trim()}
            className="rounded bg-emerald-600 px-2 py-1 text-xs text-white hover:bg-emerald-700 disabled:bg-slate-700 disabled:text-slate-500"
          >
            {saveButtonLabel}
          </button>
        )}
      </div>

      {saveError && (
        <div className="mb-2 rounded border border-red-500/30 bg-red-500/10 px-2 py-1 text-xs text-red-400">
          {saveError}
        </div>
      )}

      <div className="mb-3 shrink-0 rounded border border-emerald-700/30 bg-emerald-900/20 p-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-emerald-400">⚡</span>
            <span className="text-xs font-medium text-emerald-400">Auto Edge Creation</span>
          </div>
          <select
            value={draftMapping?.edge_preset_id ?? 'default'}
            onChange={(e) => updateDraftMapping({ edge_preset_id: e.target.value })}
            disabled={presetsLoading}
            className="rounded border border-slate-600 bg-slate-700 px-2 py-0.5 text-xs text-slate-200"
          >
            {edgePresets.map((preset) => (
              <option key={preset.id} value={preset.id}>
                {preset.name} {preset.is_builtin ? '⭐' : ''}
              </option>
            ))}
          </select>
        </div>
        {selectedPreset && (
          <div className="mt-1.5 text-[10px] text-slate-500">
            {selectedPreset.rules.length} rules • {selectedPreset.is_builtin ? 'Built-in' : 'Custom'}
          </div>
        )}
      </div>

      <div className="mb-3 flex min-h-0 flex-1 flex-col overflow-hidden">
        <div className="mb-1.5 flex shrink-0 items-center justify-between">
          <span className="text-xs font-medium text-slate-400">Mapped Fields ({fieldMappings.length})</span>
        </div>

        {fieldMappings.length === 0 ? (
          <div className="rounded border border-slate-700/50 bg-slate-800/30 py-3 text-center text-xs text-slate-500">
            Drag fields from Raw Data to Target Schema
          </div>
        ) : (
          <div className="min-h-0 flex-1 overflow-x-hidden overflow-y-auto pr-1">
            <div className="space-y-1">
              {Object.entries(mappingsByNodeType).map(([nodeType, mappings]) => (
                <div key={nodeType}>
                  <div className="sticky top-0 z-10 mb-0.5 flex items-center gap-1 bg-slate-800/90 py-0.5 text-[10px] text-slate-600">
                    <span className="rounded bg-blue-500/20 px-1 py-0.5 font-medium text-blue-400">{nodeType}</span>
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
          </div>
        )}
      </div>

      <div className="flex shrink-0 items-center gap-1.5">
        <input
          type="text"
          value={newMapping.source_path ?? ''}
          onChange={(e) => setNewMapping((prev) => ({ ...prev, source_path: e.target.value }))}
          onFocus={handleSourcePathFocus}
          className="flex-1 rounded border border-slate-600 bg-slate-700 px-2 py-1 text-xs text-slate-200"
          placeholder={selectedFieldPath ?? 'source.path'}
        />
        <input
          type="text"
          value={newMapping.target_field ?? ''}
          onChange={(e) => setNewMapping((prev) => ({ ...prev, target_field: e.target.value }))}
          className="w-20 rounded border border-slate-600 bg-slate-700 px-2 py-1 text-xs text-slate-200"
          placeholder="field"
        />
        <select
          value={newMapping.target_node_type ?? 'Service'}
          onChange={(e) => setNewMapping((prev) => ({ ...prev, target_node_type: e.target.value }))}
          className="rounded border border-slate-600 bg-slate-700 px-1.5 py-1 text-xs text-slate-200"
        >
          {NODE_TYPES.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>
        <button
          onClick={handleAddMapping}
          disabled={!newMapping.source_path || !newMapping.target_field}
          className="rounded bg-blue-600 px-2 py-1 text-xs text-white hover:bg-blue-700 disabled:bg-slate-700 disabled:text-slate-500"
        >
          +
        </button>
      </div>
    </div>
  );
}
