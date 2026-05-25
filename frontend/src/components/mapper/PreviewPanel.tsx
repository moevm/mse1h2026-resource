import { useMapperStore } from '../../store/mapperStore';

interface PreviewPanelProps {
  loading: boolean;
}

export function PreviewPanel({ loading }: PreviewPanelProps) {
  const { previewNodes, previewEdges, previewWarnings, unresolvedReferences } = useMapperStore();

  if (loading) {
    return (
      <div className="p-4 text-center text-slate-500">
        <div className="mb-2 inline-block h-6 w-6 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
        <div className="text-sm">Processing...</div>
      </div>
    );
  }

  const hasWarnings = previewWarnings.length > 0 || unresolvedReferences.length > 0;

  if (hasWarnings && previewNodes.length === 0) {
    return (
      <div className="p-3">
        {unresolvedReferences.length > 0 && (
          <div className="mb-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3">
            <div className="mb-1 flex items-center gap-2 text-sm font-medium text-amber-400">
              <span>⚠</span>
              Unresolved References ({unresolvedReferences.length})
            </div>
            <ul className="space-y-1 text-sm text-amber-300/80">
              {unresolvedReferences.map((ref, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="text-blue-400">{ref.source_node_type}</span>
                  <span className="text-slate-500">→</span>
                  <span>
                    <span className="text-slate-400">{ref.source_field}=</span>
                    <span className="text-amber-400">"{ref.expected_target_value}"</span>
                    <span className="text-slate-500"> → </span>
                    <span className="text-purple-400">{ref.expected_target_type}</span>
                    <span className="text-red-400"> not found</span>
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
        {previewWarnings.length > 0 && (
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3">
            <div className="mb-1 text-sm font-medium text-amber-400">Warnings</div>
            <ul className="list-inside list-disc text-sm text-amber-300/80">
              {previewWarnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  }

  if (previewNodes.length === 0 && previewEdges.length === 0) {
    return <div className="p-4 text-center text-sm text-slate-500">Click "Preview" to see the mapped result</div>;
  }

  return (
    <div className="p-3">
      {/* Summary */}
      <div className="mb-3 flex items-center gap-3">
        <div className="rounded-lg bg-blue-500/20 px-3 py-1">
          <span className="font-medium text-blue-400">{previewNodes.length}</span>
          <span className="ml-1 text-sm text-blue-500/70">nodes</span>
        </div>
        <div className="rounded-lg bg-emerald-500/20 px-3 py-1">
          <span className="font-medium text-emerald-400">{previewEdges.length}</span>
          <span className="ml-1 text-sm text-emerald-500/70">edges</span>
        </div>
        {unresolvedReferences.length > 0 && (
          <div className="rounded-lg bg-amber-500/20 px-3 py-1">
            <span className="font-medium text-amber-400">{unresolvedReferences.length}</span>
            <span className="ml-1 text-sm text-amber-500/70">unresolved</span>
          </div>
        )}
      </div>

      {/* Unresolved References Warning */}
      {unresolvedReferences.length > 0 && (
        <div className="mb-3 rounded-lg border border-amber-500/30 bg-amber-500/10 p-2">
          <div className="mb-1 text-xs font-medium text-amber-400">
            ⚠ Unresolved References — target nodes not found in graph
          </div>
          <div className="max-h-20 space-y-0.5 overflow-auto text-xs text-amber-300/80">
            {unresolvedReferences.map((ref, i) => (
              <div key={i}>
                <span className="text-slate-400">{ref.source_node_id.split(':').pop()}</span>
                <span className="text-slate-500">.{ref.source_field}=</span>
                <span className="text-amber-400">"{ref.expected_target_value}"</span>
                <span className="text-slate-500"> → </span>
                <span className="text-purple-400">{ref.expected_target_type}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Nodes */}
      {previewNodes.length > 0 && (
        <div className="mb-4">
          <h4 className="mb-2 text-xs font-medium tracking-wider text-slate-400 uppercase">Nodes</h4>
          <div className="max-h-48 space-y-1 overflow-auto">
            {previewNodes.map((node, i) => (
              <div key={i} className="rounded-lg border border-slate-700/50 bg-slate-800/50 p-2 text-sm">
                <div className="mb-1 flex items-center gap-2">
                  <span className="rounded bg-blue-500/20 px-1.5 py-0.5 text-xs font-medium text-blue-400">
                    {String(node.type)}
                  </span>
                  <span className="truncate font-mono text-xs text-slate-300">{String(node.id)}</span>
                </div>
                <div className="text-xs text-slate-500">
                  name: <span className="text-slate-400">{String(node.name)}</span>
                  {node.status ? (
                    <span className="ml-2">
                      status:{' '}
                      <span className="text-slate-400">
                        {typeof node.status === 'string' ? node.status : JSON.stringify(node.status)}
                      </span>
                    </span>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Edges */}
      {previewEdges.length > 0 && (
        <div>
          <h4 className="mb-2 text-xs font-medium tracking-wider text-slate-400 uppercase">Edges (auto-created)</h4>
          <div className="max-h-32 space-y-1 overflow-auto">
            {previewEdges.map((edge, i) => (
              <div key={i} className="rounded-lg border border-slate-700/50 bg-slate-800/50 p-2 text-xs">
                <span className="rounded bg-emerald-500/20 px-1.5 py-0.5 text-emerald-400">{String(edge.type)}</span>
                <span className="ml-2 text-slate-400">
                  {String(edge.source_id).split(':').pop()} <span className="text-slate-500">→</span>{' '}
                  {String(edge.target_id).split(':').pop()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
