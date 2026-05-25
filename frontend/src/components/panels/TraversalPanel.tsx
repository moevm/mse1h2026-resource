import { useCallback, useEffect, useState } from 'react';

import { executeTraversal, fetchTraversalPresets } from '../../api/graphApi';
import type { GraphResponse, TraversalPreset, TraversalRule, TraversalStep } from '../../types';
import { EdgeType, NodeType } from '../../types/enums';
import { Button } from '../common/Button';
import { Section } from '../common/Card';
import { EmptyState } from '../common/EmptyState';
import { Input } from '../common/Input';
import { IconGraph } from '../icons';

const EDGE_TYPE_VALUES = Object.values(EdgeType);
const NODE_TYPE_VALUES = Object.values(NodeType);

const DIRECTION_LABELS: Record<string, string> = {
  outgoing: '\u2192 Out',
  incoming: '\u2190 In',
  any: '\u2194 Any',
};

interface Props {
  appId?: string | null;
  onResult?: (data: GraphResponse) => void;
  onReset?: () => void;
}

export default function TraversalPanel({ appId, onResult, onReset }: Readonly<Props>) {
  const [presets, setPresets] = useState<TraversalPreset[]>([]);
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null);
  const [customMode, setCustomMode] = useState(false);

  const [ruleName, setRuleName] = useState('Custom rule');
  const [startNodeId, setStartNodeId] = useState('');
  const [startNodeTypes, setStartNodeTypes] = useState<string[]>([]);
  const [steps, setSteps] = useState<TraversalStep[]>([{ edge_types: [], direction: 'outgoing' }]);
  const [ruleLimit, setRuleLimit] = useState(100);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resultSummary, setResultSummary] = useState<string | null>(null);

  useEffect(() => {
    fetchTraversalPresets()
      .then(setPresets)
      .catch(() => setPresets([]));
  }, []);

  const handleExecute = useCallback(async () => {
    setLoading(true);
    setError(null);
    setResultSummary(null);

    let rule: TraversalRule;

    if (customMode) {
      const validSteps = steps.filter((s) => s.edge_types.length > 0);
      if (!startNodeId && startNodeTypes.length === 0) {
        setError('Choose a start node ID or at least one start node type');
        setLoading(false);
        return;
      }
      if (validSteps.length === 0) {
        setError('Add at least one traversal step with edge types');
        setLoading(false);
        return;
      }
      rule = {
        name: ruleName,
        start_node_id: startNodeId || undefined,
        start_node_types: startNodeTypes.length > 0 ? startNodeTypes : undefined,
        steps: validSteps,
        limit: ruleLimit,
      };
    } else {
      const preset = presets.find((p) => p.name === selectedPreset);
      if (!preset) {
        setError('Select a preset or switch to custom mode');
        setLoading(false);
        return;
      }
      rule = preset;
    }

    try {
      const result = await executeTraversal(rule, { appId });
      setResultSummary(`Found ${result.node_count} nodes, ${result.edge_count} edges`);
      onResult?.(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Traversal failed');
    } finally {
      setLoading(false);
    }
  }, [appId, customMode, selectedPreset, presets, ruleName, startNodeId, startNodeTypes, steps, ruleLimit, onResult]);

  const updateStep = (idx: number, patch: Partial<TraversalStep>) => {
    setSteps((prev) => prev.map((s, i) => (i === idx ? { ...s, ...patch } : s)));
  };

  const addStep = () => {
    setSteps((prev) => [...prev, { edge_types: [], direction: 'outgoing' as const }]);
  };

  const removeStep = (idx: number) => {
    setSteps((prev) => prev.filter((_, i) => i !== idx));
  };

  const toggleStepEdge = (idx: number, edge: string) => {
    const step = steps[idx];
    const edges = step.edge_types.includes(edge)
      ? step.edge_types.filter((e) => e !== edge)
      : [...step.edge_types, edge];
    updateStep(idx, { edge_types: edges });
  };

  const toggleStepNodeType = (idx: number, nt: string) => {
    const step = steps[idx];
    const types = step.target_node_types ?? [];
    const updated = types.includes(nt) ? types.filter((t) => t !== nt) : [...types, nt];
    updateStep(idx, { target_node_types: updated.length > 0 ? updated : undefined });
  };

  const toggleStepSourceNodeType = (idx: number, nt: string) => {
    const step = steps[idx];
    const types = step.source_node_types ?? [];
    const updated = types.includes(nt) ? types.filter((t) => t !== nt) : [...types, nt];
    updateStep(idx, { source_node_types: updated.length > 0 ? updated : undefined });
  };

  const toggleStartNodeType = useCallback((t: string) => {
    setStartNodeTypes((prev) => (prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]));
  }, []);

  const showPresets = !customMode;
  return (
    <div className="flex flex-col gap-4 p-4 text-sm">
      <Section title="Traversal Rules">
        <div className="flex gap-1 rounded-lg bg-slate-800/60 p-0.5">
          <button
            onClick={() => setCustomMode(false)}
            className={`flex-1 rounded-md px-2.5 py-1.5 text-xs font-medium transition-all ${
              showPresets ? 'bg-blue-600/30 text-blue-300' : 'text-slate-400 hover:text-slate-300'
            }`}
          >
            Presets
          </button>
          <button
            onClick={() => setCustomMode(true)}
            className={`flex-1 rounded-md px-2.5 py-1.5 text-xs font-medium transition-all ${
              customMode ? 'bg-blue-600/30 text-blue-300' : 'text-slate-400 hover:text-slate-300'
            }`}
          >
            Custom
          </button>
        </div>
        <p className="mt-2 rounded-md bg-slate-900/60 px-2 py-1 text-[10px] text-slate-500">
          Scope: {appId ? 'selected application' : 'current user graph'}
        </p>
      </Section>

      {showPresets && (
        <div className="space-y-1.5">
          {presets.length === 0 && (
            <EmptyState
              icon={<IconGraph className="h-7 w-7" />}
              title="No presets"
              description="Backend may be offline or no traversal presets are defined."
              className="py-4"
            />
          )}
          {presets.map((p) => (
            <button
              key={p.name}
              onClick={() => setSelectedPreset(p.name)}
              className={`w-full rounded-md px-3 py-2 text-left transition-all ${
                selectedPreset === p.name
                  ? 'bg-blue-600/20 ring-1 ring-blue-500/40'
                  : 'bg-slate-800/40 hover:bg-slate-800/70'
              }`}
            >
              <div className="text-xs font-medium text-slate-300">{p.name}</div>
              {p.description && <div className="mt-0.5 text-[10px] text-slate-500">{p.description}</div>}
              <div className="mt-1.5 space-y-1">
                {p.steps.map((step, idx) => (
                  <div key={`${p.name}-${idx}`} className="rounded bg-slate-900/50 px-2 py-1 text-[9px] text-slate-500">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-medium text-slate-400">{step.label ?? `Step ${idx + 1}`}</span>
                      <span className="shrink-0 text-slate-600">{DIRECTION_LABELS[step.direction] ?? step.direction}</span>
                    </div>
                    <div className="mt-0.5 truncate text-amber-300/80">{step.edge_types.join(', ')}</div>
                    <div className="mt-0.5 truncate">
                      {formatTypes(step.source_node_types)} {' -> '} {formatTypes(step.target_node_types)} | {step.min_depth ?? 1}-
                      {step.max_depth ?? 1} hop
                    </div>
                  </div>
                ))}
              </div>
            </button>
          ))}
        </div>
      )}

      {customMode && (
        <div className="space-y-3">
          <Input label="Name" value={ruleName} onChange={(e) => setRuleName(e.target.value)} />

          <Input
            label="Start Node ID (optional)"
            value={startNodeId}
            onChange={(e) => setStartNodeId(e.target.value)}
            placeholder="urn:service:order-service"
          />

          <div>
            <div className="mb-1 flex items-center justify-between">
              <p className="text-xs text-slate-400">Start Node Types (if no ID)</p>
              <div className="flex gap-1">
                <BulkBtn label="All" onClick={() => setStartNodeTypes([...NODE_TYPE_VALUES])} />
                <BulkBtn label="Reset" onClick={() => setStartNodeTypes([])} />
              </div>
            </div>
            <div className="flex flex-wrap gap-1">
              {NODE_TYPE_VALUES.map((t) => (
                <button
                  key={t}
                  onClick={() => toggleStartNodeType(t)}
                  className={`rounded px-1.5 py-0.5 text-[10px] font-medium transition-all ${
                    startNodeTypes.includes(t)
                      ? 'bg-emerald-600/30 text-emerald-300 ring-1 ring-emerald-500/40'
                      : 'bg-slate-800/60 text-slate-500 hover:text-slate-400'
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          <div>
            <div className="mb-1.5 flex items-center justify-between">
              <label className="text-xs text-slate-400">Traversal Steps ({steps.length})</label>
              <button
                onClick={addStep}
                className="rounded bg-slate-800/60 px-2 py-0.5 text-[10px] text-slate-400 hover:bg-slate-700/60 hover:text-slate-300"
              >
                + Add Step
              </button>
            </div>
            <div className="space-y-2">
              {steps.map((step, idx) => {
                const stepKey = `step-${idx}-${step.direction}`;
                return (
                  <div key={stepKey} className="rounded-md border border-slate-700/50 bg-slate-800/30 p-2">
                    <div className="mb-1.5 flex items-center justify-between">
                      <span className="text-[10px] font-medium text-slate-500">Step {idx + 1}</span>
                      {steps.length > 1 && (
                        <button
                          onClick={() => removeStep(idx)}
                          className="text-[10px] text-red-500/60 hover:text-red-400"
                        >
                          Remove
                        </button>
                      )}
                    </div>

                    <div className="mb-1.5 flex gap-1">
                      {(['outgoing', 'incoming', 'any'] as const).map((d) => (
                        <button
                          key={d}
                          onClick={() => updateStep(idx, { direction: d })}
                          className={`rounded px-2 py-0.5 text-[10px] transition-all ${
                            step.direction === d
                              ? 'bg-violet-600/30 text-violet-300 ring-1 ring-violet-500/40'
                              : 'bg-slate-800/60 text-slate-500'
                          }`}
                        >
                          {DIRECTION_LABELS[d] ?? d}
                        </button>
                      ))}
                    </div>

                    <div className="mb-1.5">
                      <div className="mb-0.5 flex items-center justify-between">
                        <span className="text-[10px] text-slate-500">Source types (optional):</span>
                        <div className="flex gap-1">
                          <BulkBtn
                            label="All"
                            onClick={() =>
                              updateStep(idx, {
                                source_node_types: [...NODE_TYPE_VALUES],
                              })
                            }
                          />
                          <BulkBtn
                            label="Reset"
                            onClick={() =>
                              updateStep(idx, {
                                source_node_types: undefined,
                              })
                            }
                          />
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-0.5">
                        {NODE_TYPE_VALUES.map((nt) => (
                          <button
                            key={nt}
                            onClick={() => toggleStepSourceNodeType(idx, nt)}
                            className={`rounded px-1.5 py-0.5 text-[9px] transition-all ${
                              step.source_node_types?.includes(nt)
                                ? 'bg-sky-600/30 text-sky-300 ring-1 ring-sky-500/40'
                                : 'bg-slate-800/60 text-slate-600'
                            }`}
                          >
                            {nt}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="mb-1.5">
                      <div className="mb-0.5 flex items-center justify-between">
                        <span className="text-[10px] text-slate-500">Edge types:</span>
                        <div className="flex gap-1">
                          <BulkBtn
                            label="All"
                            onClick={() =>
                              updateStep(idx, {
                                edge_types: [...EDGE_TYPE_VALUES],
                              })
                            }
                          />
                          <BulkBtn label="Reset" onClick={() => updateStep(idx, { edge_types: [] })} />
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-0.5">
                        {EDGE_TYPE_VALUES.map((e) => (
                          <button
                            key={e}
                            onClick={() => toggleStepEdge(idx, e)}
                            className={`rounded px-1.5 py-0.5 text-[9px] transition-all ${
                              step.edge_types.includes(e)
                                ? 'bg-amber-600/30 text-amber-300 ring-1 ring-amber-500/40'
                                : 'bg-slate-800/60 text-slate-600'
                            }`}
                          >
                            {e}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div>
                      <div className="mb-0.5 flex items-center justify-between">
                        <span className="text-[10px] text-slate-500">Target types (optional):</span>
                        <div className="flex gap-1">
                          <BulkBtn
                            label="All"
                            onClick={() =>
                              updateStep(idx, {
                                target_node_types: [...NODE_TYPE_VALUES],
                              })
                            }
                          />
                          <BulkBtn
                            label="Reset"
                            onClick={() =>
                              updateStep(idx, {
                                target_node_types: undefined,
                              })
                            }
                          />
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-0.5">
                        {NODE_TYPE_VALUES.map((nt) => (
                          <button
                            key={nt}
                            onClick={() => toggleStepNodeType(idx, nt)}
                            className={`rounded px-1.5 py-0.5 text-[9px] transition-all ${
                              step.target_node_types?.includes(nt)
                                ? 'bg-emerald-600/30 text-emerald-300 ring-1 ring-emerald-500/40'
                                : 'bg-slate-800/60 text-slate-600'
                            }`}
                          >
                            {nt}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <Input
            label="Result limit"
            type="number"
            value={ruleLimit}
            onChange={(e) => setRuleLimit(Number(e.target.value))}
            min={1}
            max={5000}
          />
        </div>
      )}

      {resultSummary && (
        <p className="rounded-md bg-emerald-900/20 px-2.5 py-1.5 text-xs text-emerald-400">{resultSummary}</p>
      )}

      {error && <p className="rounded-md bg-red-900/30 px-2.5 py-1.5 text-xs text-red-400">{error}</p>}

      <Button
        onClick={() => {
          void handleExecute();
        }}
        loading={loading}
        className="w-full"
      >
        Execute Traversal
      </Button>

      {onReset && (
        <Button
          variant="secondary"
          onClick={() => {
            setResultSummary(null);
            setError(null);
            onReset();
          }}
          className="w-full"
        >
          Reset to full graph
        </Button>
      )}
    </div>
  );
}

function BulkBtn({ label, onClick }: Readonly<{ label: string; onClick: () => void }>) {
  return (
    <button
      onClick={onClick}
      className="rounded bg-slate-800/60 px-1.5 py-0.5 text-[9px] text-slate-400 hover:bg-slate-700/70 hover:text-slate-200"
    >
      {label}
    </button>
  );
}

function formatTypes(types?: string[]) {
  return types && types.length > 0 ? types.join(', ') : 'any';
}
