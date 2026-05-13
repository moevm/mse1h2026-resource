import { create } from 'zustand';

import { fetchTimelineRange, type TimelineRange } from '../../../api/graphApi';
import { fetchTimelineEvents, type TimelineEvent } from '../../../api/timelineApi';

export type PlaybackSpeed = 1 | 2 | 5 | 10;

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

  fetchRange: () => Promise<void>;
  fetchEvents: (bucketSeconds?: number) => Promise<void>;
  setCurrentTime: (time: string | null) => void;
  setPlaying: (playing: boolean) => void;
  setPlaybackSpeed: (speed: PlaybackSpeed) => void;
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
};

export const useTimelineStore = create<TimelineState>((set) => ({
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

  fetchEvents: async (bucketSeconds = 30) => {
    set({ eventsLoading: true, eventsError: null });
    try {
      const resp = await fetchTimelineEvents(bucketSeconds);
      set({ events: resp.events, eventsLoading: false });
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to load timeline events';
      console.error('[Timeline] fetchEvents error:', msg);
      set({ eventsLoading: false, eventsError: msg });
    }
  },

  setCurrentTime: (time) => set({ currentTime: time }),
  setPlaying: (playing) => set({ isPlaying: playing }),
  setPlaybackSpeed: (speed) => set({ playbackSpeed: speed }),

  goLive: () => set({ currentTime: null, isPlaying: false }),

  reset: () => set(initialState),
}));
