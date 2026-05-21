import { create } from 'zustand';

import { fetchTimelineRange, type TimelineRange } from '../../../api/graphApi';
import {
  fetchTimelineEvents,
  fetchTraceActivity,
  type TimelineEvent,
  type TraceActivityBucket,
} from '../../../api/timelineApi';

export type PlaybackSpeed = 1 | 2 | 5 | 10;
export type TimelineMode = 'topology' | 'activity';

const DEFAULT_CHUNK_COUNT = 20;
const DEFAULT_BUCKET_SECONDS = 30;

interface TimelineState {
  range: TimelineRange | null;
  rangeLoading: boolean;
  rangeError: string | null;

  events: TimelineEvent[];
  activity: TraceActivityBucket[];
  eventsLoading: boolean;
  eventsError: string | null;

  currentTime: string | null;
  isPlaying: boolean;
  playbackSpeed: PlaybackSpeed;

  chunkCount: number;
  chunkBucketSeconds: number;
  windowStart: number;
  mode: TimelineMode;

  fetchRange: () => Promise<void>;
  fetchEvents: () => Promise<void>;
  setCurrentTime: (time: string | null) => void;
  setPlaying: (playing: boolean) => void;
  setPlaybackSpeed: (speed: PlaybackSpeed) => void;
  setChunkCount: (n: number) => void;
  setChunkBucketSeconds: (s: number) => void;
  setMode: (m: TimelineMode) => void;
  goLive: () => void;
  reset: () => void;
}

const initialState = {
  range: null as TimelineRange | null,
  rangeLoading: false,
  rangeError: null as string | null,
  events: [] as TimelineEvent[],
  activity: [] as TraceActivityBucket[],
  eventsLoading: false,
  eventsError: null as string | null,
  currentTime: null as string | null,
  isPlaying: false,
  playbackSpeed: 1 as PlaybackSpeed,
  chunkCount: DEFAULT_CHUNK_COUNT,
  chunkBucketSeconds: DEFAULT_BUCKET_SECONDS,
  windowStart: Date.now() - DEFAULT_CHUNK_COUNT * DEFAULT_BUCKET_SECONDS * 1000,
  mode: 'activity' as TimelineMode,
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
    const fetchStart = now - chunkCount * bucketMs * 4;
    set({ eventsLoading: true, eventsError: null });
    try {
      const fromIso = new Date(fetchStart).toISOString();
      const toIso = new Date(now).toISOString();

      const [actResp, evResp] = await Promise.all([
        fetchTraceActivity(chunkBucketSeconds, fromIso, toIso),
        fetchTimelineEvents(chunkBucketSeconds, fromIso, toIso),
      ]);
      const activity = actResp.buckets;
      const events = evResp.events;

      const nowBucket = Math.floor(now / bucketMs) * bucketMs;
      const nextStart = nowBucket - (chunkCount - 1) * bucketMs;

      set({ events, activity, eventsLoading: false, windowStart: nextStart });
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
  setChunkBucketSeconds: (s) => set({ chunkBucketSeconds: Math.max(10, Math.min(3600, Math.floor(s))) }),
  setMode: (m) => set({ mode: m, events: [], activity: [] }),

  goLive: () => set({ currentTime: null, isPlaying: false }),

  reset: () => set(initialState),
}));
