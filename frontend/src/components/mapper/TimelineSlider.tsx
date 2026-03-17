import type { RawDataChunk } from "../../types/mapper";

interface TimelineSliderProps {
  chunks: RawDataChunk[];
  selectedChunk: RawDataChunk | null;
  onSelectChunk: (chunk: RawDataChunk | null) => void;
  loading: boolean;
}

export function TimelineSlider({
  chunks,
  selectedChunk,
  onSelectChunk,
  loading,
}: TimelineSliderProps) {
  if (loading) {
    return (
      <div className="bg-slate-800/50 px-4 py-2 border-b border-slate-700/50 shrink-0">
        <div className="text-sm text-slate-500">Loading chunks...</div>
      </div>
    );
  }

  if (chunks.length === 0) {
    return (
      <div className="bg-slate-800/50 px-4 py-2 border-b border-slate-700/50 shrink-0">
        <div className="text-sm text-slate-500">No data chunks available</div>
      </div>
    );
  }

  // Format timestamp for display
  const formatTime = (isoString: string) => {
    const date = new Date(isoString);
    return date.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  const formatDate = (isoString: string) => {
    const date = new Date(isoString);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    });
  };

  // Group chunks by date
  const chunksByDate = chunks.reduce((acc, chunk) => {
    const date = formatDate(chunk.timestamp);
    if (!acc[date]) {
      acc[date] = [];
    }
    acc[date].push(chunk);
    return acc;
  }, {} as Record<string, RawDataChunk[]>);

  return (
    <div className="bg-slate-800/50 px-4 py-2 border-b border-slate-700/50 shrink-0">
      <div className="flex items-center gap-4">
        <span className="text-sm text-slate-400 shrink-0">
          {chunks.length} chunk{chunks.length !== 1 ? "s" : ""}
        </span>

        {/* Timeline */}
        <div className="flex-1 flex items-center gap-1 overflow-x-auto py-1">
          {Object.entries(chunksByDate).map(([date, dateChunks]) => (
            <div key={date} className="flex items-center gap-1 shrink-0">
              <span className="text-xs text-slate-600 px-2">{date}</span>
              {dateChunks.map((chunk) => (
                <button
                  key={chunk.id}
                  onClick={() => onSelectChunk(chunk)}
                  className={`px-2 py-1 rounded text-xs font-mono transition-colors ${
                    selectedChunk?.id === chunk.id
                      ? "bg-blue-600 text-white"
                      : chunk.is_processed
                      ? "bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30"
                      : "bg-slate-700 text-slate-300 hover:bg-slate-600"
                  }`}
                  title={`${formatTime(chunk.timestamp)} - ${chunk.size_bytes} bytes`}
                >
                  {formatTime(chunk.timestamp)}
                  {chunk.is_processed && " ✓"}
                </button>
              ))}
            </div>
          ))}
        </div>

        {/* Selected chunk info */}
        {selectedChunk && (
          <div className="text-xs text-slate-500 flex items-center gap-3 shrink-0">
            <span>
              {(selectedChunk.size_bytes / 1024).toFixed(1)} KB
            </span>
            <span className="text-slate-600">
              {selectedChunk.agent_id.slice(0, 8)}
            </span>
            {selectedChunk.is_processed && (
              <span className="text-emerald-400">Processed</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
