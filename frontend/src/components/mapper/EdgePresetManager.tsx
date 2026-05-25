import { useEffect, useState } from 'react';

import { mapperApi } from '../../api/mapperApi';
import type { AutoEdgeRule, EdgePreset } from '../../types/mapper';

const NODE_TYPES = [
  'Service',
  'Endpoint',
  'Deployment',
  'Pod',
  'Node',
  'Database',
  'Table',
  'QueueTopic',
  'Cache',
  'ExternalAPI',
  'SecretConfig',
  'Library',
  'TeamOwner',
  'SLASLO',
  'RegionCluster',
];

const EDGE_TYPES = [
  { value: 'calls', label: 'calls — HTTP/gRPC' },
  { value: 'deployedon', label: 'deployedon — placement' },
  { value: 'dependson', label: 'depends_on — infra' },
  { value: 'reads', label: 'reads — DB read' },
  { value: 'writes', label: 'writes — DB write' },
  { value: 'publishesto', label: 'publishes_to — queue' },
  { value: 'consumesfrom', label: 'consumes_from — queue' },
  { value: 'ownedby', label: 'owned_by — ownership' },
  { value: 'authenticatesvia', label: 'authenticates_via — auth' },
  { value: 'ratelimitedby', label: 'rate_limited_by' },
  { value: 'fails_over_to', label: 'fails_over_to — failover' },
];

interface RuleEditorProps {
  rule: AutoEdgeRule;
  onChange: (rule: AutoEdgeRule) => void;
  onRemove: () => void;
}

function RuleEditor({ rule, onChange, onRemove }: RuleEditorProps) {
  return (
    <div className="rounded-lg border border-slate-700/50 bg-slate-800/50 p-2.5 text-xs">
      <div className="grid grid-cols-[1fr_auto_1fr_auto_1fr_auto] items-center gap-2">
        {/* Source Type */}
        <div>
          <label
            htmlFor={`rule-source-${rule.id}`}
            className="mb-0.5 block text-[10px] tracking-wide text-slate-500 uppercase"
          >
            Source
          </label>
          <select
            id={`rule-source-${rule.id}`}
            value={rule.source_type}
            onChange={(e) => onChange({ ...rule, source_type: e.target.value })}
            className="w-full rounded border border-slate-600 bg-slate-700 px-2 py-1.5 text-slate-200"
          >
            {NODE_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>

        {/* Source Field */}
        <div className="w-28">
          <label
            htmlFor={`rule-sfield-${rule.id}`}
            className="mb-0.5 block text-[10px] tracking-wide text-slate-500 uppercase"
          >
            Field
          </label>
          <input
            id={`rule-sfield-${rule.id}`}
            type="text"
            value={rule.source_field}
            onChange={(e) => onChange({ ...rule, source_field: e.target.value })}
            placeholder="node_name"
            className="w-full rounded border border-slate-600 bg-slate-700 px-2 py-1.5 text-slate-200"
          />
        </div>

        {/* Edge Type */}
        <div>
          <label
            htmlFor={`rule-edge-${rule.id}`}
            className="mb-0.5 block text-[10px] tracking-wide text-slate-500 uppercase"
          >
            Edge
          </label>
          <select
            id={`rule-edge-${rule.id}`}
            value={rule.edge_type}
            onChange={(e) => onChange({ ...rule, edge_type: e.target.value })}
            className="w-full rounded border border-slate-600 bg-slate-700 px-2 py-1.5 text-slate-200"
          >
            {EDGE_TYPES.map((e) => (
              <option key={e.value} value={e.value}>
                {e.value}
              </option>
            ))}
          </select>
        </div>

        {/* Target Type */}
        <div>
          <label
            htmlFor={`rule-target-${rule.id}`}
            className="mb-0.5 block text-[10px] tracking-wide text-slate-500 uppercase"
          >
            Target
          </label>
          <select
            id={`rule-target-${rule.id}`}
            value={rule.target_type}
            onChange={(e) => onChange({ ...rule, target_type: e.target.value })}
            className="w-full rounded border border-slate-600 bg-slate-700 px-2 py-1.5 text-slate-200"
          >
            {NODE_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>

        {/* Target Field */}
        <div className="w-28">
          <label
            htmlFor={`rule-tfield-${rule.id}`}
            className="mb-0.5 block text-[10px] tracking-wide text-slate-500 uppercase"
          >
            T.Field
          </label>
          <input
            id={`rule-tfield-${rule.id}`}
            type="text"
            value={rule.target_field}
            onChange={(e) => onChange({ ...rule, target_field: e.target.value })}
            placeholder="name"
            className="w-full rounded border border-slate-600 bg-slate-700 px-2 py-1.5 text-slate-200"
          />
        </div>

        {/* Delete */}
        <div className="self-end">
          <button
            onClick={onRemove}
            className="rounded p-1.5 text-red-500/70 hover:bg-red-500/10 hover:text-red-400"
            title="Remove rule"
          >
            ✕
          </button>
        </div>
      </div>
    </div>
  );
}

interface EdgePresetManagerProps {
  onSelectPreset?: (presetId: string) => void;
  selectedPresetId?: string | null;
}

export function EdgePresetManager({ onSelectPreset, selectedPresetId }: EdgePresetManagerProps) {
  const [presets, setPresets] = useState<EdgePreset[]>([]);
  const [loading, setLoading] = useState(false);
  const [editingPreset, setEditingPreset] = useState<EdgePreset | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  // Load presets
  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const response = await mapperApi.listEdgePresets();
        if (!cancelled) setPresets(response.presets);
      } catch (error) {
        console.error('Failed to load edge presets:', error);
        // intentional
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleCreateNew = () => {
    setIsCreating(true);
    setEditingPreset({
      id: '',
      name: 'New Preset',
      description: '',
      rules: [],
      is_builtin: false,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      created_by: 'user',
    });
  };

  const handleSave = async () => {
    if (!editingPreset) return;

    try {
      if (isCreating) {
        const created = await mapperApi.createEdgePreset({
          name: editingPreset.name,
          description: editingPreset.description ?? undefined,
          rules: editingPreset.rules,
        });
        setPresets([...presets, created]);
        setIsCreating(false);
      } else {
        const updated = await mapperApi.updateEdgePreset(editingPreset.id, {
          name: editingPreset.name,
          description: editingPreset.description ?? undefined,
          rules: editingPreset.rules,
        });
        setPresets(presets.map((p) => (p.id === updated.id ? updated : p)));
      }
      setEditingPreset(null);
    } catch (error) {
      console.error('Failed to save preset:', error);
      alert('Failed to save preset');
    }
  };

  const handleDelete = async (presetId: string) => {
    if (!confirm('Delete this preset?')) return;

    try {
      await mapperApi.deleteEdgePreset(presetId);
      setPresets(presets.filter((p) => p.id !== presetId));
    } catch (error) {
      console.error('Failed to delete preset:', error);
      alert('Failed to delete preset');
    }
  };

  const addRule = () => {
    if (!editingPreset) return;
    const newRule: AutoEdgeRule = {
      id: `rule-${Date.now()}`,
      source_type: 'Service',
      source_field: '',
      target_type: 'Service',
      target_field: 'name',
      edge_type: 'calls',
    };
    setEditingPreset({ ...editingPreset, rules: [...editingPreset.rules, newRule] });
  };

  const updateRule = (index: number, rule: AutoEdgeRule) => {
    if (!editingPreset) return;
    const newRules = [...editingPreset.rules];
    newRules[index] = rule;
    setEditingPreset({ ...editingPreset, rules: newRules });
  };

  const removeRule = (index: number) => {
    if (!editingPreset) return;
    setEditingPreset({
      ...editingPreset,
      rules: editingPreset.rules.filter((_, i) => i !== index),
    });
  };

  if (loading) {
    return <div className="p-8 text-center text-sm text-slate-500">Loading presets...</div>;
  }

  // Editing mode
  if (editingPreset) {
    return (
      <div className="flex h-full flex-col p-4">
        <div className="mb-4 flex shrink-0 items-center justify-between">
          <h3 className="text-base font-medium text-slate-200">{isCreating ? 'Create New Preset' : 'Edit Preset'}</h3>
          <div className="flex gap-2">
            <button
              onClick={() => {
                setEditingPreset(null);
                setIsCreating(false);
              }}
              className="rounded border border-slate-700 px-3 py-1.5 text-sm text-slate-500 hover:border-slate-600 hover:text-slate-400"
            >
              Cancel
            </button>
            <button
              onClick={() => {
                void handleSave();
              }}
              disabled={!editingPreset.name || editingPreset.rules.length === 0}
              className="rounded bg-emerald-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:bg-slate-700 disabled:text-slate-500"
            >
              Save Preset
            </button>
          </div>
        </div>

        {/* Preset name & description */}
        <div className="mb-4 shrink-0 space-y-3">
          <div>
            <label htmlFor="preset-name" className="mb-1 block text-xs tracking-wide text-slate-500 uppercase">
              Preset Name
            </label>
            <input
              id="preset-name"
              type="text"
              value={editingPreset.name}
              onChange={(e) => setEditingPreset({ ...editingPreset, name: e.target.value })}
              placeholder="My Custom Edge Rules"
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200"
            />
          </div>
          <div>
            <label htmlFor="preset-desc" className="mb-1 block text-xs tracking-wide text-slate-500 uppercase">
              Description
            </label>
            <input
              id="preset-desc"
              type="text"
              value={editingPreset.description ?? ''}
              onChange={(e) => setEditingPreset({ ...editingPreset, description: e.target.value })}
              placeholder="What does this preset do?"
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200"
            />
          </div>
        </div>

        {/* Rules list */}
        <div className="flex min-h-0 flex-1 flex-col">
          <div className="mb-2 flex shrink-0 items-center justify-between">
            <span className="text-sm font-medium text-slate-300">Rules ({editingPreset.rules.length})</span>
            <button onClick={addRule} className="rounded bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700">
              + Add Rule
            </button>
          </div>

          {editingPreset.rules.length === 0 ? (
            <div className="flex flex-1 items-center justify-center rounded-lg border border-slate-700/50 bg-slate-800/30 text-sm text-slate-500">
              <div className="text-center">
                <div className="mb-1 text-slate-400">No rules defined</div>
                <div className="text-xs text-slate-600">Add rules to define automatic edge creation</div>
              </div>
            </div>
          ) : (
            <div className="flex-1 space-y-2 overflow-auto pr-1">
              {editingPreset.rules.map((rule, index) => (
                <RuleEditor
                  key={rule.id}
                  rule={rule}
                  onChange={(r) => updateRule(index, r)}
                  onRemove={() => removeRule(index)}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  // List mode
  return (
    <div className="flex h-full flex-col p-4">
      <div className="mb-3 flex shrink-0 items-center justify-between">
        <div>
          <h3 className="text-base font-medium text-slate-200">Available Presets</h3>
          <p className="mt-0.5 text-xs text-slate-500">Select a preset for automatic edge creation</p>
        </div>
        <button
          onClick={handleCreateNew}
          className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
        >
          + Create New
        </button>
      </div>

      <div className="flex-1 overflow-auto">
        <div className="grid gap-2">
          {presets.map((preset) => (
            <div
              key={preset.id}
              role="button"
              tabIndex={0}
              className={[
                'cursor-pointer rounded-lg border p-3 transition-all',
                selectedPresetId === preset.id
                  ? 'border-blue-500/60 bg-blue-500/15 ring-1 ring-blue-500/30'
                  : 'border-slate-700/50 bg-slate-800/50 hover:border-slate-600 hover:bg-slate-800/80',
              ].join(' ')}
              onClick={() => onSelectPreset?.(preset.id)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') onSelectPreset?.(preset.id);
              }}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-slate-200">{preset.name}</span>
                    {preset.is_builtin && (
                      <span className="rounded bg-amber-500/20 px-1.5 py-0.5 text-[10px] font-medium text-amber-400">
                        ⭐ built-in
                      </span>
                    )}
                    {selectedPresetId === preset.id && (
                      <span className="rounded bg-blue-500/20 px-1.5 py-0.5 text-[10px] font-medium text-blue-400">
                        ✓ selected
                      </span>
                    )}
                  </div>
                  <div className="mt-0.5 text-xs text-slate-500">
                    {preset.rules.length} rules
                    {preset.description && ` • ${preset.description}`}
                  </div>
                </div>
                <div className="ml-2 flex items-center gap-1">
                  {!preset.is_builtin && (
                    <>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setEditingPreset(preset);
                        }}
                        className="rounded px-2 py-1 text-xs text-slate-500 hover:bg-slate-700/50 hover:text-slate-300"
                      >
                        Edit
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          void handleDelete(preset.id);
                        }}
                        className="rounded px-2 py-1 text-xs text-red-500/60 hover:bg-red-500/10 hover:text-red-400"
                      >
                        Delete
                      </button>
                    </>
                  )}
                </div>
              </div>

              {/* Show rules preview */}
              {selectedPresetId === preset.id && preset.rules.length > 0 && (
                <div className="mt-3 border-t border-slate-700/50 pt-3">
                  <div className="mb-2 text-[10px] tracking-wide text-slate-500 uppercase">Rules</div>
                  <div className="grid grid-cols-2 gap-1 text-xs">
                    {preset.rules.slice(0, 8).map((rule) => (
                      <div
                        key={rule.id}
                        className="flex items-center gap-1 rounded bg-slate-800/30 px-2 py-1 text-slate-400"
                      >
                        <span className="text-blue-400">{rule.source_type}</span>
                        <span className="text-slate-600">.</span>
                        <span className="truncate">{rule.source_field}</span>
                        <span className="text-slate-600">→</span>
                        <span className="text-purple-400">{rule.target_type}</span>
                        <span className="ml-auto text-[10px] text-emerald-500">({rule.edge_type})</span>
                      </div>
                    ))}
                    {preset.rules.length > 8 && (
                      <div className="col-span-2 py-1 text-center text-xs text-slate-600">
                        +{preset.rules.length - 8} more rules
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
