import { useState } from 'react';

import { useAgents } from '../../hooks/useAgents';
import { Badge } from '../common/Badge';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
import { EmptyState } from '../common/EmptyState';
import { Input } from '../common/Input';
import { Select } from '../common/Select';
import { IconAgents, IconClock, IconPlus, IconRefresh, IconX } from '../icons';

const SOURCE_TYPE_OPTIONS = [
  { value: 'watcher-otel-traces', label: 'OTel Traces Watcher' },
  { value: 'watcher-kubernetes-objects', label: 'Kubernetes Watcher' },
  { value: 'otel-collector', label: 'OpenTelemetry Collector' },
  { value: 'k8s-agent', label: 'Kubernetes Agent' },
  { value: 'aws-agent', label: 'AWS Agent' },
  { value: 'mock', label: 'Mock' },
  { value: 'custom', label: 'Custom' },
];

export function AgentsPage() {
  const { agents, loading, error, register, reload } = useAgents();
  const [showForm, setShowForm] = useState(false);
  const [createdToken, setCreatedToken] = useState<{ agentName: string; token: string } | null>(null);

  return (
    <div className="animate-fade-in h-full space-y-5 overflow-y-auto p-6">
      {}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-slate-100">Agents</h1>
          <p className="mt-0.5 text-xs text-slate-500">Manage data collection agents</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            icon={<IconRefresh className="h-3.5 w-3.5" />}
            onClick={() => {
              void reload();
            }}
          >
            Refresh
          </Button>
          <Button
            variant={showForm ? 'secondary' : 'primary'}
            size="sm"
            icon={showForm ? <IconX className="h-3.5 w-3.5" /> : <IconPlus className="h-3.5 w-3.5" />}
            onClick={() => setShowForm((s) => !s)}
          >
            {showForm ? 'Cancel' : 'Register Agent'}
          </Button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-3 rounded-xl border border-red-800/60 bg-red-950/60 px-4 py-3 text-sm text-red-300">
          <span className="shrink-0">⚠</span>
          <span>{error}</span>
        </div>
      )}

      {/* Token display after registration */}
      {createdToken && (
        <Card title="✅ Agent Registered — Save Your Token!">
          <div className="space-y-3">
            <p className="text-sm text-slate-300">
              Agent <span className="font-semibold text-white">{createdToken.agentName}</span> registered successfully.
              Set this token as{' '}
              <code className="rounded bg-slate-800 px-1.5 py-0.5 text-xs text-amber-400">AGENT_TOKEN</code> environment
              variable in your watcher configuration.
            </p>
            <div className="flex items-center gap-2">
              <code className="flex-1 rounded-lg border border-slate-700 bg-slate-950 px-4 py-3 font-mono text-sm break-all text-amber-300 select-all">
                {createdToken.token}
              </code>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  void navigator.clipboard.writeText(createdToken.token);
                }}
              >
                Copy
              </Button>
            </div>
            <p className="text-xs text-red-400">⚠ This token will not be shown again. Copy it now.</p>
            <Button variant="ghost" size="sm" onClick={() => setCreatedToken(null)}>
              Dismiss
            </Button>
          </div>
        </Card>
      )}

      {}
      {showForm && (
        <RegisterForm
          onSubmit={async (req) => {
            const result = await register(req);
            setShowForm(false);
            if (result) {
              setCreatedToken({ agentName: result.name, token: result.token });
            }
          }}
        />
      )}

      {/* Skeleton loading */}
      {loading && (
        <div className="grid gap-3">
          {[1, 2, 3].map((i) => (
            <AgentCardSkeleton key={i} />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && agents.length === 0 && (
        <EmptyState
          icon={<IconAgents className="h-12 w-12" />}
          title="No agents registered"
          description="Register an agent to start collecting topology data."
          action={
            <Button
              variant="primary"
              size="sm"
              icon={<IconPlus className="h-3.5 w-3.5" />}
              onClick={() => setShowForm(true)}
            >
              Register Agent
            </Button>
          }
        />
      )}

      {/* Agents list */}
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
    app_id?: string;
    app_name?: string;
  };
}

function AgentCardSkeleton() {
  return (
    <div className="flex animate-pulse items-center gap-4 rounded-xl border border-slate-800/80 bg-slate-900 p-4">
      <div className="h-10 w-10 rounded-xl bg-slate-800" />
      <div className="min-w-0 flex-1 space-y-2">
        <div className="flex items-center gap-2">
          <div className="h-4 w-32 rounded bg-slate-800" />
          <div className="h-5 w-20 rounded-full bg-slate-800" />
        </div>
        <div className="h-3 w-48 rounded bg-slate-800" />
        <div className="h-2.5 w-64 rounded bg-slate-800" />
      </div>
      <div className="shrink-0 space-y-1 text-right">
        <div className="h-3 w-28 rounded bg-slate-800" />
        <div className="h-3 w-24 rounded bg-slate-800" />
      </div>
    </div>
  );
}

function AgentCard({ agent }: Readonly<AgentCardProps>) {
  return (
    <div className="flex items-center gap-4 rounded-xl border border-slate-800/80 bg-slate-900 p-4 transition-colors hover:border-slate-700/80">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-slate-700/60 bg-slate-800 text-slate-400">
        <IconAgents className="h-5 w-5" />
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-semibold text-slate-100">{agent.name}</span>
          <Badge label={agent.source_type} color="#6366f1" />
          {agent.app_name && <Badge label={agent.app_name} color="#10b981" />}
        </div>
        {agent.description && <p className="mt-0.5 truncate text-xs text-slate-500">{agent.description}</p>}
        <p className="mt-1 truncate font-mono text-[10px] text-slate-600">{agent.agent_id}</p>
      </div>

      <div className="shrink-0 space-y-0.5 text-right text-[11px] text-slate-500">
        {agent.registered_at && (
          <p className="flex items-center justify-end gap-1">
            <IconClock className="h-3 w-3" />
            Registered: <span className="text-slate-400">{new Date(agent.registered_at).toLocaleDateString()}</span>
          </p>
        )}
        {agent.last_seen_at && (
          <p className="flex items-center justify-end gap-1">
            <IconClock className="h-3 w-3" />
            Last seen: <span className="text-slate-400">{new Date(agent.last_seen_at).toLocaleString()}</span>
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
  token?: string;
  app_token?: string;
}

function RegisterForm({
  onSubmit,
}: Readonly<{
  onSubmit: (req: RegisterRequest) => Promise<void>;
}>) {
  const [name, setName] = useState('');
  const [sourceType, setSourceType] = useState('custom');
  const [description, setDescription] = useState('');
  const [agentToken, setAgentToken] = useState('');
  const [appToken, setAppToken] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: { preventDefault(): void }) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await onSubmit({
        name: name.trim(),
        source_type: sourceType,
        description: description.trim() || undefined,
        token: agentToken.trim() || undefined,
        app_token: appToken.trim() || undefined,
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
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
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
          label="Agent Token"
          placeholder="Token from watcher config (AGENT_TOKEN). Leave empty to auto-generate."
          value={agentToken}
          onChange={(e) => setAgentToken(e.target.value)}
        />
        <p className="-mt-2 text-xs text-slate-500">
          Set this to the same value as AGENT_TOKEN in your watcher's environment. If empty, a token will be generated
          for you.
        </p>
        <Input
          label="Description"
          placeholder="Optional description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <Input
          label="Application Token (optional)"
          placeholder="Paste app_token to bind to application"
          value={appToken}
          onChange={(e) => setAppToken(e.target.value)}
        />
        <Button type="submit" variant="primary" size="md" loading={submitting} disabled={!name.trim()}>
          {submitting ? 'Registering…' : 'Register Agent'}
        </Button>
      </form>
    </Card>
  );
}
