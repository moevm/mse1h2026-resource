import { create } from 'zustand';

import { fetchTimelineRange, type TimelineRange } from '../../../api/graphApi';
import { fetchTimelineEvents, type TimelineEvent } from '../../../api/timelineApi';

export type PlaybackSpeed = 1 | 2 | 5 | 10;

// Default rolling-window shape: 20 chunks of 30s = 10-minute view.
const DEFAULT_CHUNK_COUNT = 20;
const DEFAULT_BUCKET_SECONDS = 30;

interface TimelineState {
  range: TimelineRange | null;
  rangeLoading: boolean;
  rangeError: string | null;

  events: TimelineEvent[];
  eventsLoading: boolean;
  eventsError: string | null;

  currentTime: string | null; // null = live
  isPlaying: boolean;
  playbackSpeed: PlaybackSpeed;

  // Rolling window config. Window length = chunkCount * chunkBucketSeconds.
  // The window is LEFT-anchored: windowStart is bucket-aligned to the oldest
  // event in view (or "now" if there are none). New events arriving past
  // windowEnd slide the window forward, dropping the oldest bucket.
  chunkCount: number;
  chunkBucketSeconds: number;
  windowStart: number; // unix ms, bucket-aligned

  fetchRange: () => Promise<void>;
  fetchEvents: () => Promise<void>;
  setCurrentTime: (time: string | null) => void;
  setPlaying: (playing: boolean) => void;
  setPlaybackSpeed: (speed: PlaybackSpeed) => void;
  setChunkCount: (n: number) => void;
  setChunkBucketSeconds: (s: number) => void;
  goLive: () => void;
  reset: () => void;
}

const initialState = {
  range: null as TimelineRange | null,
  rangeLoading: false,
  rangeError: null as string | null,
  events: [] as TimelineEvent[],
  eventsLoading: false,
  eventsError: null as string | null,
  currentTime: null as string | null,
  isPlaying: false,
  playbackSpeed: 1 as PlaybackSpeed,
  chunkCount: DEFAULT_CHUNK_COUNT,
  chunkBucketSeconds: DEFAULT_BUCKET_SECONDS,
  windowStart: Date.now() - DEFAULT_CHUNK_COUNT * DEFAULT_BUCKET_SECONDS * 1000,
};

export const useTimelineStore = create<TimelineState>((set, get) => ({
  ...initialState,

  fetchRange: async () => {
    set({ rangeLoading: true, rangeError: null });
    try {
      const range = await fetchTimelineRange();
      set({ range, rangeLoading: false });
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to load timeline range';
      console.error('[Timeline] fetchRange error:', msg);
      set({ rangeLoading: false, rangeError: msg });
    }
  },

  fetchEvents: async () => {
    const { chunkCount, chunkBucketSeconds } = get();
    const bucketMs = chunkBucketSeconds * 1000;
    const now = Date.now();
    // Fetch a generous tail so we can detect activity that just happened.
    // The render side will pick where to anchor the visible window.
    const fetchStart = now - chunkCount * bucketMs * 4;
    set({ eventsLoading: true, eventsError: null });
    try {
      const resp = await fetchTimelineEvents(
        chunkBucketSeconds,
        new Date(fetchStart).toISOString(),
        new Date(now).toISOString(),
      );

      // Left-anchored window: snap the start to the bucket containing the
      // earliest event we got (so the first bar lands at slot 0). If we have
      // no events, keep the window pinned at "now - N*bucket" so Live still
      // sits at the right edge.
      let nextStart: number;
      if (resp.events.length > 0) {
        const earliest = Math.min(
          ...resp.events.map((e) => new Date(e.timestamp).getTime()),
        );
        nextStart = Math.floor(earliest / bucketMs) * bucketMs;

        // If new events arrived past the window, slide forward so they fit.
        const latest = Math.max(
          ...resp.events.map((e) => new Date(e.timestamp).getTime()),
        );
        const windowEnd = nextStart + chunkCount * bucketMs;
        if (latest >= windowEnd) {
          nextStart = Math.floor((latest - (chunkCount - 1) * bucketMs) / bucketMs) * bucketMs;
        }
      } else {
        nextStart = now - chunkCount * bucketMs;
      }

      set({ events: resp.events, eventsLoading: false, windowStart: nextStart });
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to load timeline events';
      console.error('[Timeline] fetchEvents error:', msg);
      set({ eventsLoading: false, eventsError: msg });
    }
  },

  setCurrentTime: (time) => set({ currentTime: time }),
  setPlaying: (playing) => set({ isPlaying: playing }),
  setPlaybackSpeed: (speed) => set({ playbackSpeed: speed }),
  setChunkCount: (n) => set({ chunkCount: Math.max(2, Math.min(120, Math.floor(n))) }),
  setChunkBucketSeconds: (s) => set({ chunkBucketSeconds: Math.max(1, Math.min(3600, Math.floor(s))) }),

  goLive: () => set({ currentTime: null, isPlaying: false }),

  reset: () => set(initialState),
}));
