import type { ReactNode } from "react";

interface InfoRowProps {
    label: string;
    value: string;
    warn?: boolean;
    icon?: ReactNode;
}

export function InfoRow({ label, value, warn, icon }: Readonly<InfoRowProps>) {
    return (
        <div className="flex justify-between items-center text-sm py-0.5">
            <span className="text-slate-400 flex items-center gap-2">
                {icon}
                {label}
            </span>
            <span
                className="font-mono font-medium"
                style={{ color: warn ? "#ef4444" : "#e2e8f0" }}
            >
                {value}
            </span>
        </div>
    );
}
