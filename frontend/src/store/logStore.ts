import { create } from "zustand";
import type { LogEntry, LogLevel } from "../types";

export interface LogState {
    entries: LogEntry[];
    maxEntries: number;
    filterLevel: LogLevel | "all";
    filterSource: string;

    addEntry: (entry: Omit<LogEntry, "id" | "timestamp">) => void;
    addLog: (
        level: LogLevel,
        source: string,
        message: string,
        details?: Record<string, unknown>,
    ) => void;
    clearLogs: () => void;
    setFilterLevel: (level: LogLevel | "all") => void;
    setFilterSource: (source: string) => void;
    getFilteredEntries: () => LogEntry[];
}

let _logCounter = 0;

function createLogEntry(
    level: LogLevel,
    source: string,
    message: string,
    details?: Record<string, unknown>,
): LogEntry {
    _logCounter += 1;
    return {
        id: `log-${Date.now()}-${_logCounter}`,
        timestamp: new Date().toISOString(),
        level,
        source,
        message,
        details,
    };
}

export const useLogStore = create<LogState>((set, get) => ({
    entries: [],
    maxEntries: 500,
    filterLevel: "all",
    filterSource: "",

    addEntry: (entry) =>
        set((s) => {
            const newEntry = createLogEntry(
                entry.level,
                entry.source,
                entry.message,
                entry.details,
            );
            const entries = [newEntry, ...s.entries].slice(0, s.maxEntries);
            return { entries };
        }),

    addLog: (level, source, message, details) =>
        set((s) => {
            const newEntry = createLogEntry(level, source, message, details);
            const entries = [newEntry, ...s.entries].slice(0, s.maxEntries);
            return { entries };
        }),

    clearLogs: () => set({ entries: [] }),

    setFilterLevel: (level) => set({ filterLevel: level }),

    setFilterSource: (source) => set({ filterSource: source }),

    getFilteredEntries: () => {
        const { entries, filterLevel, filterSource } = get();
        return entries.filter((e) => {
            if (filterLevel !== "all" && e.level !== filterLevel) return false;
            if (filterSource && !e.source.toLowerCase().includes(filterSource.toLowerCase()))
                return false;
            return true;
        });
    },
}));
