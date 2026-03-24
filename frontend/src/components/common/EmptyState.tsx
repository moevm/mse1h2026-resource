import type { ReactNode } from "react";

interface EmptyStateProps {
    icon?: ReactNode;
    title: string;
    description?: string;
    action?: ReactNode;
    className?: string;
}

export function EmptyState({
    icon,
    title,
    description,
    action,
    className = "",
}: Readonly<EmptyStateProps>) {
    return (
        <div
            className={`flex flex-col items-center justify-center text-center gap-4 py-16 px-8 animate-fade-in ${className}`}
        >
            {icon && (
                <div className="text-slate-500 p-4 rounded-2xl bg-slate-800/50 border border-slate-700/50">
                    {icon}
                </div>
            )}
            <div className="space-y-2">
                <p className="text-base font-medium text-slate-300">{title}</p>
                {description && (
                    <p className="text-sm text-slate-500 max-w-sm leading-relaxed">{description}</p>
                )}
            </div>
            {action && <div className="mt-2">{action}</div>}
        </div>
    );
}
