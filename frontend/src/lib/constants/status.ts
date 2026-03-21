export const STATUS_CONFIG = {
    connected: {
        color: "bg-emerald-500",
        label: "Connected",
    },
    disconnected: {
        color: "bg-red-500",
        label: "Disconnected",
    },
    checking: {
        color: "bg-amber-500 animate-pulse",
        label: "Checking…",
    },
} as const;

export type ConnectionStatus = keyof typeof STATUS_CONFIG;
