import { useState, useEffect, useCallback } from "react";
import { fetchTraversalPresets, executeTraversal } from "../../api/graphApi";
import type { TraversalPreset, TraversalRule, TraversalStep, GraphResponse } from "../../types";
import { NodeType, EdgeType } from "../../types/enums";
import { Button } from "../common/Button";
import { Input } from "../common/Input";
import { Section } from "../common/Card";
import { EmptyState } from "../common/EmptyState";
import { IconGraph } from "../icons";

const EDGE_TYPE_VALUES = Object.values(EdgeType);
const NODE_TYPE_VALUES = Object.values(NodeType);

const DIRECTION_LABELS: Record<string, string> = {
    outgoing: "\u2192 Out",
    incoming: "\u2190 In",
    any: "\u2194 Any",
};

interface Props {
    onResult?: (data: GraphResponse) => void;
}

export default function TraversalPanel({ onResult }: Readonly<Props>) {
    const [presets, setPresets] = useState<TraversalPreset[]>([]);
    const [selectedPreset, setSelectedPreset] = useState<string | null>(null);
    const [customMode, setCustomMode] = useState(false);

    const [ruleName, setRuleName] = useState("Custom rule");
    const [startNodeId, setStartNodeId] = useState("");
    const [startNodeTypes, setStartNodeTypes] = useState<string[]>([]);
    const [steps, setSteps] = useState<TraversalStep[]>([
        { edge_types: [], direction: "outgoing" },
    ]);
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
            rule = {
                name: ruleName,
                start_node_id: startNodeId || undefined,
                start_node_types: startNodeTypes.length > 0 ? startNodeTypes : undefined,
                steps: steps.filter((s) => s.edge_types.length > 0),
                limit: ruleLimit,
            };
        } else {
            const preset = presets.find((p) => p.name === selectedPreset);
            if (!preset) {
                setError("Select a preset or switch to custom mode");
                setLoading(false);
                return;
            }
            rule = preset;
        }

        try {
            const result = await executeTraversal(rule);
            setResultSummary(`Found ${result.node_count} nodes, ${result.edge_count} edges`);
            onResult?.(result);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Traversal failed");
        } finally {
            setLoading(false);
        }
    }, [
        customMode,
        selectedPreset,
        presets,
        ruleName,
        startNodeId,
        startNodeTypes,
        steps,
        ruleLimit,
        onResult,
    ]);

    const updateStep = (idx: number, patch: Partial<TraversalStep>) => {
        setSteps((prev) => prev.map((s, i) => (i === idx ? { ...s, ...patch } : s)));
    };

    const addStep = () => {
        setSteps((prev) => [...prev, { edge_types: [], direction: "outgoing" as const }]);
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

    const toggleStartNodeType = useCallback((t: string) => {
        setStartNodeTypes((prev) =>
            prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t],
        );
    }, []);

    const showPresets = !customMode;
    return (
        <div className="flex flex-col gap-4 p-4 text-sm">
            <Section title="Traversal Rules">
                <div className="flex gap-1 rounded-lg bg-slate-800/60 p-0.5">
                    <button
                        onClick={() => setCustomMode(false)}
                        className={`flex-1 rounded-md px-2.5 py-1.5 text-xs font-medium transition-all ${
                            showPresets
                                ? "bg-blue-600/30 text-blue-300"
                                : "text-slate-400 hover:text-slate-300"
                        }`}
                    >
                        Presets
                    </button>
                    <button
                        onClick={() => setCustomMode(true)}
                        className={`flex-1 rounded-md px-2.5 py-1.5 text-xs font-medium transition-all ${
                            customMode
                                ? "bg-blue-600/30 text-blue-300"
                                : "text-slate-400 hover:text-slate-300"
                        }`}
                    >
                        Custom
                    </button>
                </div>
            </Section>

            {showPresets && (
                <div className="space-y-1.5">
                    {presets.length === 0 && (
                        <EmptyState
                            icon={<IconGraph className="w-7 h-7" />}
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
                                    ? "bg-blue-600/20 ring-1 ring-blue-500/40"
                                    : "bg-slate-800/40 hover:bg-slate-800/70"
                            }`}
                        >
                            <div className="text-xs font-medium text-slate-300">{p.name}</div>
                            {p.description && (
                                <div className="mt-0.5 text-[10px] text-slate-500">
                                    {p.description}
                                </div>
                            )}
                        </button>
                    ))}
                </div>
            )}

            {customMode && (
                <div className="space-y-3">
                    <Input
                        label="Name"
                        value={ruleName}
                        onChange={(e) => setRuleName(e.target.value)}
                    />

                    <Input
                        label="Start Node ID (optional)"
                        value={startNodeId}
                        onChange={(e) => setStartNodeId(e.target.value)}
                        placeholder="urn:service:order-service"
                    />

                    <div>
                        <p className="mb-1 text-xs text-slate-400">Start Node Types (if no ID)</p>
                        <div className="flex flex-wrap gap-1">
                            {NODE_TYPE_VALUES.map((t) => (
                                <button
                                    key={t}
                                    onClick={() => toggleStartNodeType(t)}
                                    className={`rounded px-1.5 py-0.5 text-[10px] font-medium transition-all ${
                                        startNodeTypes.includes(t)
                                            ? "bg-emerald-600/30 text-emerald-300 ring-1 ring-emerald-500/40"
                                            : "bg-slate-800/60 text-slate-500 hover:text-slate-400"
                                    }`}
                                >
                                    {t}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div>
                        <div className="mb-1.5 flex items-center justify-between">
                            <label className="text-xs text-slate-400">
                                Traversal Steps ({steps.length})
                            </label>
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
                                    <div
                                        key={stepKey}
                                        className="rounded-md border border-slate-700/50 bg-slate-800/30 p-2"
                                    >
                                        <div className="mb-1.5 flex items-center justify-between">
                                            <span className="text-[10px] font-medium text-slate-500">
                                                Step {idx + 1}
                                            </span>
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
                                            {(["outgoing", "incoming", "any"] as const).map((d) => (
                                                <button
                                                    key={d}
                                                    onClick={() =>
                                                        updateStep(idx, { direction: d })
                                                    }
                                                    className={`rounded px-2 py-0.5 text-[10px] transition-all ${
                                                        step.direction === d
                                                            ? "bg-violet-600/30 text-violet-300 ring-1 ring-violet-500/40"
                                                            : "bg-slate-800/60 text-slate-500"
                                                    }`}
                                                >
                                                    {DIRECTION_LABELS[d] ?? d}
                                                </button>
                                            ))}
                                        </div>

                                        <div className="mb-1.5">
                                            <div className="mb-0.5 text-[10px] text-slate-500">
                                                Edge types:
                                            </div>
                                            <div className="flex flex-wrap gap-0.5">
                                                {EDGE_TYPE_VALUES.map((e) => (
                                                    <button
                                                        key={e}
                                                        onClick={() => toggleStepEdge(idx, e)}
                                                        className={`rounded px-1.5 py-0.5 text-[9px] transition-all ${
                                                            step.edge_types.includes(e)
                                                                ? "bg-amber-600/30 text-amber-300 ring-1 ring-amber-500/40"
                                                                : "bg-slate-800/60 text-slate-600"
                                                        }`}
                                                    >
                                                        {e}
                                                    </button>
                                                ))}
                                            </div>
                                        </div>

                                        <div>
                                            <div className="mb-0.5 text-[10px] text-slate-500">
                                                Target types (optional):
                                            </div>
                                            <div className="flex flex-wrap gap-0.5">
                                                {NODE_TYPE_VALUES.map((nt) => (
                                                    <button
                                                        key={nt}
                                                        onClick={() => toggleStepNodeType(idx, nt)}
                                                        className={`rounded px-1.5 py-0.5 text-[9px] transition-all ${
                                                            step.target_node_types?.includes(nt)
                                                                ? "bg-emerald-600/30 text-emerald-300 ring-1 ring-emerald-500/40"
                                                                : "bg-slate-800/60 text-slate-600"
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
                <p className="rounded-md bg-emerald-900/20 px-2.5 py-1.5 text-xs text-emerald-400">
                    {resultSummary}
                </p>
            )}

            {error && (
                <p className="rounded-md bg-red-900/30 px-2.5 py-1.5 text-xs text-red-400">
                    {error}
                </p>
            )}

            <Button
                onClick={() => {
                    void handleExecute();
                }}
                loading={loading}
                className="w-full"
            >
                Execute Traversal
            </Button>
        </div>
    );
}
