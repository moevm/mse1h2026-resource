import { formatTime } from '../../lib/utils/format';
import type { RawDataChunk } from '../../types/mapper';

interface TimelineSliderProps {
  chunks: RawDataChunk[];
  selectedChunk: RawDataChunk | null;
  onSelectChunk: (chunk: RawDataChunk | null) => void;
  onPinChunk?: (chunkId: string) => Promise<void>;
  onUnpinChunk?: (chunkId: string) => Promise<void>;
  loading: boolean;
  sampleChunkId?: string | null;
  showPinning?: boolean;
}

export function TimelineSlider({
  chunks,
  selectedChunk,
  onSelectChunk,
  onPinChunk,
  onUnpinChunk,
  loading,
  sampleChunkId,
  showPinning = false,
}: TimelineSliderProps) {
  if (loading) {
    return (
      <div className="shrink-0 border-b border-slate-700/50 bg-slate-800/50 px-4 py-2">
        <div className="text-sm text-slate-500">Loading chunks...</div>
      </div>
    );
  }

  if (chunks.length === 0) {
    return (
      <div className="shrink-0 border-b border-slate-700/50 bg-slate-800/50 px-4 py-2">
        <div className="text-sm text-slate-500">No data chunks available</div>
      </div>
    );
  }

  const formatDate = (isoString: string) => {
    const date = new Date(isoString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
  };

  const chunksByDate = chunks.reduce(
    (acc, chunk) => {
      const date = formatDate(chunk.timestamp);
      if (!acc[date]) {
        acc[date] = [];
      }
      acc[date].push(chunk);
      return acc;
    },
    {} as Record<string, RawDataChunk[]>,
  );

  return (
    <div className="shrink-0 border-b border-slate-700/50 bg-slate-800/50 px-4 py-2">
      <div className="flex items-center gap-4">
        <span className="shrink-0 text-sm text-slate-400">
          {chunks.length} chunk{chunks.length !== 1 ? 's' : ''}
        </span>

        <div className="scrollbar-thin scrollbar-thumb-slate-600 scrollbar-track-transparent flex-1 overflow-x-auto overflow-y-hidden">
          <div className="flex items-center gap-1 py-1">
            {Object.entries(chunksByDate).map(([date, dateChunks]) => (
              <div key={date} className="flex shrink-0 items-center gap-1">
                <span className="px-2 text-xs text-slate-600">{date}</span>
                {dateChunks.map((chunk) => {
                  const isSelected = selectedChunk?.id === chunk.id;
                  const isSample = sampleChunkId === chunk.id;

                  return (
                    <button
                      key={chunk.id}
                      onClick={() => onSelectChunk(chunk)}
                      className={`shrink-0 rounded px-2 py-1 font-mono text-xs transition-colors ${
                        isSelected
                          ? 'bg-blue-600 text-white'
                          : isSample
                            ? 'border border-purple-500/50 bg-purple-500/30 text-purple-300 hover:bg-purple-500/40'
                            : showPinning && chunk.is_pinned
                              ? 'border border-amber-500/40 bg-amber-500/20 text-amber-300 hover:bg-amber-500/30'
                              : chunk.is_processed
                                ? 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30'
                                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                      }`}
                      title={`${formatTime(chunk.timestamp)} - ${chunk.size_bytes} bytes${isSample ? ' (sample chunk)' : ''}${showPinning && chunk.is_pinned ? ' (pinned)' : ''}`}
                    >
                      {formatTime(chunk.timestamp)}
                      {isSample && ' ★'}
                      {showPinning && chunk.is_pinned && ' 📌'}
                      {chunk.is_processed && ' ✓'}
                    </button>
                  );
                })}
              </div>
            ))}
          </div>
        </div>

        {selectedChunk && (
          <div className="flex shrink-0 items-center gap-3 text-xs text-slate-500">
            <span>{(selectedChunk.size_bytes / 1024).toFixed(1)} KB</span>
            <span className="text-slate-600">{selectedChunk.agent_id.slice(0, 8)}</span>
            {selectedChunk.chunk_type_label && (
              <span className="text-slate-500">{selectedChunk.chunk_type_label}</span>
            )}
            {selectedChunk.is_processed && <span className="text-emerald-400">Processed</span>}
            {showPinning && selectedChunk.is_pinned ? (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  void onUnpinChunk?.(selectedChunk.id);
                }}
                className="text-amber-400 transition-colors hover:text-amber-300"
                title="Unpin chunk"
              >
                📌 Pinned
              </button>
            ) : showPinning ? (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  void onPinChunk?.(selectedChunk.id);
                }}
                className="text-slate-500 transition-colors hover:text-amber-400"
                title="Pin chunk (prevent expiry)"
              >
                Pin
              </button>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}
