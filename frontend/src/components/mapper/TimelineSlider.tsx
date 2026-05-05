import type { RawDataChunk } from "../../types/mapper";
import { formatTime } from "../../lib/utils/format";

interface TimelineSliderProps {
  chunks: RawDataChunk[];
  selectedChunk: RawDataChunk | null;
  onSelectChunk: (chunk: RawDataChunk | null) => void;
  onPinChunk?: (chunkId: string) => Promise<void>;
  onUnpinChunk?: (chunkId: string) => Promise<void>;
  loading: boolean;
  sampleChunkId?: string | null;
}

export function TimelineSlider({
  chunks,
  selectedChunk,
  onSelectChunk,
  onPinChunk,
  onUnpinChunk,
  loading,
  sampleChunkId,
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

  const formatDate = (isoString: string) => {
    const date = new Date(isoString);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    });
  };

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

        
        <div className="flex-1 overflow-x-auto overflow-y-hidden scrollbar-thin scrollbar-thumb-slate-600 scrollbar-track-transparent">
          <div className="flex items-center gap-1 py-1">
            {Object.entries(chunksByDate).map(([date, dateChunks]) => (
              <div key={date} className="flex items-center gap-1 shrink-0">
                <span className="text-xs text-slate-600 px-2">{date}</span>
                {dateChunks.map((chunk) => {
                  const isSelected = selectedChunk?.id === chunk.id;
                  const isSample = sampleChunkId === chunk.id;

                  return (
                    <button
                      key={chunk.id}
                      onClick={() => onSelectChunk(chunk)}
                      className={`px-2 py-1 rounded text-xs font-mono transition-colors shrink-0 ${
                        isSelected
                          ? "bg-blue-600 text-white"
                          : isSample
                          ? "bg-purple-500/30 text-purple-300 border border-purple-500/50 hover:bg-purple-500/40"
                          : chunk.is_pinned
                          ? "bg-amber-500/20 text-amber-300 border border-amber-500/40 hover:bg-amber-500/30"
                          : chunk.is_processed
                          ? "bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30"
                          : "bg-slate-700 text-slate-300 hover:bg-slate-600"
                      }`}
                      title={`${formatTime(chunk.timestamp)} - ${chunk.size_bytes} bytes${isSample ? ' (sample chunk)' : ''}${chunk.is_pinned ? ' (pinned)' : ''}`}
                    >
                      {formatTime(chunk.timestamp)}
                      {isSample && " ★"}
                      {chunk.is_pinned && " 📌"}
                      {chunk.is_processed && " ✓"}
                    </button>
                  );
                })}
              </div>
            ))}
          </div>
        </div>

        
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
            {selectedChunk.is_pinned ? (
              <button
                onClick={async (e) => {
                  e.stopPropagation();
                  onUnpinChunk && await onUnpinChunk(selectedChunk.id);
                }}
                className="text-amber-400 hover:text-amber-300 transition-colors"
                title="Unpin chunk"
              >
                📌 Pinned
              </button>
            ) : (
              <button
                onClick={async (e) => {
                  e.stopPropagation();
                  onPinChunk && await onPinChunk(selectedChunk.id);
                }}
                className="text-slate-500 hover:text-amber-400 transition-colors"
                title="Pin chunk (prevent expiry)"
              >
                Pin
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
