import { useMapperStore } from "../../store/mapperStore";

interface PreviewPanelProps {
  loading: boolean;
}

export function PreviewPanel({ loading }: PreviewPanelProps) {
  const { previewNodes, previewEdges, previewWarnings, unresolvedReferences } = useMapperStore();

  if (loading) {
    return (
      <div className="p-4 text-center text-slate-500">
        <div className="animate-spin inline-block w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full mb-2"></div>
        <div className="text-sm">Processing...</div>
      </div>
    );
  }

  const hasWarnings = previewWarnings.length > 0 || unresolvedReferences.length > 0;

  if (hasWarnings && previewNodes.length === 0) {
    return (
      <div className="p-3">
        {unresolvedReferences.length > 0 && (
          <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3 mb-2">
            <div className="font-medium text-amber-400 mb-1 text-sm flex items-center gap-2">
              <span>⚠</span>
              Unresolved References ({unresolvedReferences.length})
            </div>
            <ul className="text-sm text-amber-300/80 space-y-1">
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
          <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3">
            <div className="font-medium text-amber-400 mb-1 text-sm">Warnings</div>
            <ul className="text-sm text-amber-300/80 list-disc list-inside">
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
    return (
      <div className="p-4 text-center text-slate-500 text-sm">
        Click "Preview" to see the mapped result
      </div>
    );
  }

  return (
    <div className="p-3">
      {/* Summary */}
      <div className="flex items-center gap-3 mb-3">
        <div className="bg-blue-500/20 px-3 py-1 rounded-lg">
          <span className="text-blue-400 font-medium">{previewNodes.length}</span>
          <span className="text-blue-500/70 text-sm ml-1">nodes</span>
        </div>
        <div className="bg-emerald-500/20 px-3 py-1 rounded-lg">
          <span className="text-emerald-400 font-medium">{previewEdges.length}</span>
          <span className="text-emerald-500/70 text-sm ml-1">edges</span>
        </div>
        {unresolvedReferences.length > 0 && (
          <div className="bg-amber-500/20 px-3 py-1 rounded-lg">
            <span className="text-amber-400 font-medium">{unresolvedReferences.length}</span>
            <span className="text-amber-500/70 text-sm ml-1">unresolved</span>
          </div>
        )}
      </div>

      {/* Unresolved References Warning */}
      {unresolvedReferences.length > 0 && (
        <div className="mb-3 bg-amber-500/10 border border-amber-500/30 rounded-lg p-2">
          <div className="text-xs font-medium text-amber-400 mb-1">
            ⚠ Unresolved References — target nodes not found in graph
          </div>
          <div className="text-xs text-amber-300/80 space-y-0.5 max-h-20 overflow-auto">
            {unresolvedReferences.map((ref, i) => (
              <div key={i}>
                <span className="text-slate-400">{ref.source_node_id.split(":").pop()}</span>
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
          <h4 className="text-xs font-medium text-slate-400 mb-2 uppercase tracking-wider">Nodes</h4>
          <div className="space-y-1 max-h-48 overflow-auto">
            {previewNodes.map((node, i) => (
              <div
                key={i}
                className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-2 text-sm"
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="px-1.5 py-0.5 bg-blue-500/20 text-blue-400 rounded text-xs font-medium">
                    {String(node.type)}
                  </span>
                  <span className="font-mono text-slate-300 truncate text-xs">
                    {String(node.id)}
                  </span>
                </div>
                <div className="text-xs text-slate-500">
                  name: <span className="text-slate-400">{String(node.name)}</span>
                  {node.status ? (
                    <span className="ml-2">
                      status: <span className="text-slate-400">{String(node.status)}</span>
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
          <h4 className="text-xs font-medium text-slate-400 mb-2 uppercase tracking-wider">Edges (auto-created)</h4>
          <div className="space-y-1 max-h-32 overflow-auto">
            {previewEdges.map((edge, i) => (
              <div
                key={i}
                className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-2 text-xs"
              >
                <span className="px-1.5 py-0.5 bg-emerald-500/20 text-emerald-400 rounded">
                  {String(edge.type)}
                </span>
                <span className="text-slate-400 ml-2">
                  {String(edge.source_id).split(":").pop()} <span className="text-slate-500">→</span> {String(edge.target_id).split(":").pop()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
