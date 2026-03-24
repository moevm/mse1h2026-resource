import { useState, useEffect } from "react";
import { mapperApi } from "../../api/mapperApi";
import type { EdgePreset, AutoEdgeRule } from "../../types/mapper";

const NODE_TYPES = [
  "Service", "Endpoint", "Deployment", "Pod", "Node",
  "Database", "Table", "QueueTopic", "Cache", "ExternalAPI",
  "SecretConfig", "Library", "TeamOwner", "SLASLO", "RegionCluster",
];

const EDGE_TYPES = [
  { value: "calls", label: "calls — HTTP/gRPC" },
  { value: "deployedon", label: "deployedon — placement" },
  { value: "dependson", label: "depends_on — infra" },
  { value: "reads", label: "reads — DB read" },
  { value: "writes", label: "writes — DB write" },
  { value: "publishesto", label: "publishes_to — queue" },
  { value: "consumesfrom", label: "consumes_from — queue" },
  { value: "ownedby", label: "owned_by — ownership" },
  { value: "authenticatesvia", label: "authenticates_via — auth" },
  { value: "ratelimitedby", label: "rate_limited_by" },
  { value: "fails_over_to", label: "fails_over_to — failover" },
];

interface RuleEditorProps {
  rule: AutoEdgeRule;
  onChange: (rule: AutoEdgeRule) => void;
  onRemove: () => void;
}

function RuleEditor({ rule, onChange, onRemove }: RuleEditorProps) {
  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-2.5 text-xs">
      <div className="grid grid-cols-[1fr_auto_1fr_auto_1fr_auto] gap-2 items-center">
        {/* Source Type */}
        <div>
          <label className="block text-slate-500 mb-0.5 text-[10px] uppercase tracking-wide">Source</label>
          <select
            value={rule.source_type}
            onChange={(e) => onChange({ ...rule, source_type: e.target.value })}
            className="w-full px-2 py-1.5 bg-slate-700 border border-slate-600 rounded text-slate-200"
          >
            {NODE_TYPES.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>

        {/* Source Field */}
        <div className="w-28">
          <label className="block text-slate-500 mb-0.5 text-[10px] uppercase tracking-wide">Field</label>
          <input
            type="text"
            value={rule.source_field}
            onChange={(e) => onChange({ ...rule, source_field: e.target.value })}
            placeholder="node_name"
            className="w-full px-2 py-1.5 bg-slate-700 border border-slate-600 rounded text-slate-200"
          />
        </div>

        {/* Edge Type */}
        <div>
          <label className="block text-slate-500 mb-0.5 text-[10px] uppercase tracking-wide">Edge</label>
          <select
            value={rule.edge_type}
            onChange={(e) => onChange({ ...rule, edge_type: e.target.value })}
            className="w-full px-2 py-1.5 bg-slate-700 border border-slate-600 rounded text-slate-200"
          >
            {EDGE_TYPES.map((e) => (
              <option key={e.value} value={e.value}>{e.value}</option>
            ))}
          </select>
        </div>

        {/* Target Type */}
        <div>
          <label className="block text-slate-500 mb-0.5 text-[10px] uppercase tracking-wide">Target</label>
          <select
            value={rule.target_type}
            onChange={(e) => onChange({ ...rule, target_type: e.target.value })}
            className="w-full px-2 py-1.5 bg-slate-700 border border-slate-600 rounded text-slate-200"
          >
            {NODE_TYPES.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>

        {/* Target Field */}
        <div className="w-28">
          <label className="block text-slate-500 mb-0.5 text-[10px] uppercase tracking-wide">T.Field</label>
          <input
            type="text"
            value={rule.target_field}
            onChange={(e) => onChange({ ...rule, target_field: e.target.value })}
            placeholder="name"
            className="w-full px-2 py-1.5 bg-slate-700 border border-slate-600 rounded text-slate-200"
          />
        </div>

        {/* Delete */}
        <div className="self-end">
          <button
            onClick={onRemove}
            className="text-red-500/70 hover:text-red-400 p-1.5 hover:bg-red-500/10 rounded"
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
    loadPresets();
  }, []);

  const loadPresets = async () => {
    setLoading(true);
    try {
      const response = await mapperApi.listEdgePresets();
      setPresets(response.presets);
    } catch (error) {
      console.error("Failed to load edge presets:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateNew = () => {
    setIsCreating(true);
    setEditingPreset({
      id: "",
      name: "New Preset",
      description: "",
      rules: [],
      is_builtin: false,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      created_by: "user",
    });
  };

  const handleSave = async () => {
    if (!editingPreset) return;

    try {
      if (isCreating) {
        const created = await mapperApi.createEdgePreset({
          name: editingPreset.name,
          description: editingPreset.description || undefined,
          rules: editingPreset.rules,
        });
        setPresets([...presets, created]);
        setIsCreating(false);
      } else {
        const updated = await mapperApi.updateEdgePreset(editingPreset.id, {
          name: editingPreset.name,
          description: editingPreset.description || undefined,
          rules: editingPreset.rules,
        });
        setPresets(presets.map((p) => (p.id === updated.id ? updated : p)));
      }
      setEditingPreset(null);
    } catch (error) {
      console.error("Failed to save preset:", error);
      alert("Failed to save preset");
    }
  };

  const handleDelete = async (presetId: string) => {
    if (!confirm("Delete this preset?")) return;

    try {
      await mapperApi.deleteEdgePreset(presetId);
      setPresets(presets.filter((p) => p.id !== presetId));
    } catch (error) {
      console.error("Failed to delete preset:", error);
      alert("Failed to delete preset");
    }
  };

  const addRule = () => {
    if (!editingPreset) return;
    const newRule: AutoEdgeRule = {
      id: `rule-${Date.now()}`,
      source_type: "Service",
      source_field: "",
      target_type: "Service",
      target_field: "name",
      edge_type: "calls",
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
    return <div className="p-8 text-slate-500 text-sm text-center">Loading presets...</div>;
  }

  // Editing mode
  if (editingPreset) {
    return (
      <div className="p-4 h-full flex flex-col">
        <div className="flex items-center justify-between mb-4 shrink-0">
          <h3 className="text-base font-medium text-slate-200">
            {isCreating ? "Create New Preset" : "Edit Preset"}
          </h3>
          <div className="flex gap-2">
            <button
              onClick={() => {
                setEditingPreset(null);
                setIsCreating(false);
              }}
              className="text-sm text-slate-500 hover:text-slate-400 px-3 py-1.5 border border-slate-700 rounded hover:border-slate-600"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={!editingPreset.name || editingPreset.rules.length === 0}
              className="text-sm bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-700 disabled:text-slate-500 text-white px-4 py-1.5 rounded font-medium"
            >
              Save Preset
            </button>
          </div>
        </div>

        {/* Preset name & description */}
        <div className="mb-4 space-y-3 shrink-0">
          <div>
            <label className="block text-xs text-slate-500 mb-1 uppercase tracking-wide">Preset Name</label>
            <input
              type="text"
              value={editingPreset.name}
              onChange={(e) => setEditingPreset({ ...editingPreset, name: e.target.value })}
              placeholder="My Custom Edge Rules"
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-200"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1 uppercase tracking-wide">Description</label>
            <input
              type="text"
              value={editingPreset.description || ""}
              onChange={(e) => setEditingPreset({ ...editingPreset, description: e.target.value })}
              placeholder="What does this preset do?"
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-200"
            />
          </div>
        </div>

        {/* Rules list */}
        <div className="flex-1 flex flex-col min-h-0">
          <div className="flex items-center justify-between mb-2 shrink-0">
            <span className="text-sm font-medium text-slate-300">
              Rules ({editingPreset.rules.length})
            </span>
            <button
              onClick={addRule}
              className="text-sm bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded"
            >
              + Add Rule
            </button>
          </div>

          {editingPreset.rules.length === 0 ? (
            <div className="flex-1 flex items-center justify-center text-sm text-slate-500 bg-slate-800/30 rounded-lg border border-slate-700/50">
              <div className="text-center">
                <div className="text-slate-400 mb-1">No rules defined</div>
                <div className="text-xs text-slate-600">Add rules to define automatic edge creation</div>
              </div>
            </div>
          ) : (
            <div className="flex-1 overflow-auto space-y-2 pr-1">
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
    <div className="p-4 h-full flex flex-col">
      <div className="flex items-center justify-between mb-3 shrink-0">
        <div>
          <h3 className="text-base font-medium text-slate-200">Available Presets</h3>
          <p className="text-xs text-slate-500 mt-0.5">Select a preset for automatic edge creation</p>
        </div>
        <button
          onClick={handleCreateNew}
          className="text-sm bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded font-medium"
        >
          + Create New
        </button>
      </div>

      <div className="flex-1 overflow-auto">
        <div className="grid gap-2">
          {presets.map((preset) => (
            <div
              key={preset.id}
              className={[
                "p-3 rounded-lg border cursor-pointer transition-all",
                selectedPresetId === preset.id
                  ? "bg-blue-500/15 border-blue-500/60 ring-1 ring-blue-500/30"
                  : "bg-slate-800/50 border-slate-700/50 hover:border-slate-600 hover:bg-slate-800/80",
              ].join(" ")}
              onClick={() => onSelectPreset?.(preset.id)}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-slate-200">{preset.name}</span>
                    {preset.is_builtin && (
                      <span className="text-[10px] px-1.5 py-0.5 bg-amber-500/20 text-amber-400 rounded font-medium">
                        ⭐ built-in
                      </span>
                    )}
                    {selectedPresetId === preset.id && (
                      <span className="text-[10px] px-1.5 py-0.5 bg-blue-500/20 text-blue-400 rounded font-medium">
                        ✓ selected
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-slate-500 mt-0.5">
                    {preset.rules.length} rules
                    {preset.description && ` • ${preset.description}`}
                  </div>
                </div>
                <div className="flex items-center gap-1 ml-2">
                  {!preset.is_builtin && (
                    <>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setEditingPreset(preset);
                        }}
                        className="text-slate-500 hover:text-slate-300 hover:bg-slate-700/50 px-2 py-1 rounded text-xs"
                      >
                        Edit
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(preset.id);
                        }}
                        className="text-red-500/60 hover:text-red-400 hover:bg-red-500/10 px-2 py-1 rounded text-xs"
                      >
                        Delete
                      </button>
                    </>
                  )}
                </div>
              </div>

              {/* Show rules preview */}
              {selectedPresetId === preset.id && preset.rules.length > 0 && (
                <div className="mt-3 pt-3 border-t border-slate-700/50">
                  <div className="text-[10px] text-slate-500 uppercase tracking-wide mb-2">Rules</div>
                  <div className="grid grid-cols-2 gap-1 text-xs">
                    {preset.rules.slice(0, 8).map((rule) => (
                      <div key={rule.id} className="flex items-center gap-1 text-slate-400 bg-slate-800/30 px-2 py-1 rounded">
                        <span className="text-blue-400">{rule.source_type}</span>
                        <span className="text-slate-600">.</span>
                        <span className="truncate">{rule.source_field}</span>
                        <span className="text-slate-600">→</span>
                        <span className="text-purple-400">{rule.target_type}</span>
                        <span className="text-emerald-500 text-[10px] ml-auto">({rule.edge_type})</span>
                      </div>
                    ))}
                    {preset.rules.length > 8 && (
                      <div className="text-slate-600 text-xs col-span-2 text-center py-1">
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
