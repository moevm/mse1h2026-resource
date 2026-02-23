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
            className={`flex flex-col items-center justify-center text-center gap-3 py-12 px-6 ${className}`}
        >
            {icon && <div className="text-slate-600 opacity-50 mb-1">{icon}</div>}
            <div>
                <p className="text-sm font-medium text-slate-400">{title}</p>
                {description && (
                    <p className="text-xs text-slate-600 mt-1 max-w-xs">{description}</p>
                )}
            </div>
            {action && <div className="mt-1">{action}</div>}
        </div>
    );
}
