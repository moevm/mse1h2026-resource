import { useState } from "react";
import { useAgents } from "../../hooks/useAgents";
import { Spinner } from "../common/Spinner";
import { Badge } from "../common/Badge";
import { Button } from "../common/Button";
import { Input } from "../common/Input";
import { Select } from "../common/Select";
import { Card } from "../common/Card";
import { EmptyState } from "../common/EmptyState";
import { IconAgents, IconRefresh, IconPlus, IconX, IconClock } from "../icons";

const SOURCE_TYPE_OPTIONS = [
    { value: "otel-collector", label: "OpenTelemetry Collector" },
    { value: "k8s-agent", label: "Kubernetes Agent" },
    { value: "aws-agent", label: "AWS Agent" },
    { value: "mock", label: "Mock" },
    { value: "custom", label: "Custom" },
];

export function AgentsPage() {
    const { agents, loading, error, register, reload } = useAgents();
    const [showForm, setShowForm] = useState(false);

    return (
        <div className="p-6 space-y-5 overflow-y-auto h-full animate-fade-in">
            {}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-lg font-semibold text-slate-100">Agents</h1>
                    <p className="text-xs text-slate-500 mt-0.5">Manage data collection agents</p>
                </div>
                <div className="flex items-center gap-2">
                    <Button
                        variant="ghost"
                        size="sm"
                        icon={<IconRefresh className="w-3.5 h-3.5" />}
                        onClick={() => {
                            void reload();
                        }}
                    >
                        Refresh
                    </Button>
                    <Button
                        variant={showForm ? "secondary" : "primary"}
                        size="sm"
                        icon={
                            showForm ? (
                                <IconX className="w-3.5 h-3.5" />
                            ) : (
                                <IconPlus className="w-3.5 h-3.5" />
                            )
                        }
                        onClick={() => setShowForm((s) => !s)}
                    >
                        {showForm ? "Cancel" : "Register Agent"}
                    </Button>
                </div>
            </div>

            {error && (
                <div className="flex items-center gap-3 bg-red-950/60 text-red-300 text-sm px-4 py-3 rounded-xl border border-red-800/60">
                    <span className="shrink-0">⚠</span>
                    <span>{error}</span>
                </div>
            )}

            {}
            {showForm && (
                <RegisterForm
                    onSubmit={async (req) => {
                        await register(req);
                        setShowForm(false);
                    }}
                />
            )}

            {}
            {loading && (
                <div className="flex justify-center py-16">
                    <Spinner size="lg" label="Loading agents…" />
                </div>
            )}

            {}
            {!loading && agents.length === 0 && (
                <EmptyState
                    icon={<IconAgents className="w-12 h-12" />}
                    title="No agents registered"
                    description="Register an agent to start collecting topology data."
                    action={
                        <Button
                            variant="primary"
                            size="sm"
                            icon={<IconPlus className="w-3.5 h-3.5" />}
                            onClick={() => setShowForm(true)}
                        >
                            Register Agent
                        </Button>
                    }
                />
            )}

            {}
            {!loading && agents.length > 0 && (
                <div className="grid gap-3">
                    {agents.map((agent) => (
                        <AgentCard key={agent.agent_id} agent={agent} />
                    ))}
                </div>
            )}
        </div>
    );
}

interface AgentCardProps {
    agent: {
        agent_id: string;
        name: string;
        source_type: string;
        description?: string;
        registered_at?: string;
        last_seen_at?: string;
    };
}

function AgentCard({ agent }: Readonly<AgentCardProps>) {
    return (
        <div className="flex items-center gap-4 bg-slate-900 border border-slate-800/80 rounded-xl p-4 hover:border-slate-700/80 transition-colors">
            <div className="h-10 w-10 rounded-xl bg-slate-800 border border-slate-700/60 flex items-center justify-center text-slate-400 shrink-0">
                <IconAgents className="w-5 h-5" />
            </div>

            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-semibold text-slate-100">{agent.name}</span>
                    <Badge label={agent.source_type} color="#6366f1" />
                </div>
                {agent.description && (
                    <p className="text-xs text-slate-500 mt-0.5 truncate">{agent.description}</p>
                )}
                <p className="text-[10px] text-slate-600 font-mono mt-1 truncate">
                    {agent.agent_id}
                </p>
            </div>

            <div className="text-right text-[11px] text-slate-500 shrink-0 space-y-0.5">
                {agent.registered_at && (
                    <p className="flex items-center justify-end gap-1">
                        <IconClock className="w-3 h-3" />
                        Registered:{" "}
                        <span className="text-slate-400">
                            {new Date(agent.registered_at).toLocaleDateString()}
                        </span>
                    </p>
                )}
                {agent.last_seen_at && (
                    <p className="flex items-center justify-end gap-1">
                        <IconClock className="w-3 h-3" />
                        Last seen:{" "}
                        <span className="text-slate-400">
                            {new Date(agent.last_seen_at).toLocaleString()}
                        </span>
                    </p>
                )}
            </div>
        </div>
    );
}

interface RegisterRequest {
    name: string;
    source_type: string;
    description?: string;
}

function RegisterForm({
    onSubmit,
}: Readonly<{
    onSubmit: (req: RegisterRequest) => Promise<void>;
}>) {
    const [name, setName] = useState("");
    const [sourceType, setSourceType] = useState("custom");
    const [description, setDescription] = useState("");
    const [submitting, setSubmitting] = useState(false);

    const handleSubmit = async (e: { preventDefault(): void }) => {
        e.preventDefault();
        setSubmitting(true);
        try {
            await onSubmit({
                name: name.trim(),
                source_type: sourceType,
                description: description.trim() || undefined,
            });
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <Card title="Register New Agent">
            <form
                onSubmit={(e) => {
                    void handleSubmit(e);
                }}
                className="space-y-4"
            >
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <Input
                        label="Agent Name"
                        placeholder="my-otel-collector"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        required
                    />
                    <Select
                        label="Source Type"
                        value={sourceType}
                        options={SOURCE_TYPE_OPTIONS}
                        onChange={(e) => setSourceType(e.target.value)}
                    />
                </div>
                <Input
                    label="Description"
                    placeholder="Optional description"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                />
                <Button
                    type="submit"
                    variant="primary"
                    size="md"
                    loading={submitting}
                    disabled={!name.trim()}
                >
                    {submitting ? "Registering…" : "Register Agent"}
                </Button>
            </form>
        </Card>
    );
}
