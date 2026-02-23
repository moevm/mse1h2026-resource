import type { ReactNode } from "react";

interface CardProps {
    title?: string;
    description?: string;
    action?: ReactNode;
    children: ReactNode;
    className?: string;
    noPadding?: boolean;
}

export function Card({
    title,
    description,
    action,
    children,
    className = "",
    noPadding = false,
}: Readonly<CardProps>) {
    const hasMeta = title != null || description != null || action != null;

    return (
        <div
            className={`rounded-xl bg-slate-900 border border-slate-800 overflow-hidden ${className}`}
        >
            {hasMeta && (
                <div className="flex items-start justify-between gap-4 px-4 pt-4 pb-3 border-b border-slate-800/60">
                    <div className="min-w-0">
                        {title && (
                            <h2 className="text-sm font-semibold text-slate-200 leading-tight">
                                {title}
                            </h2>
                        )}
                        {description && (
                            <p className="text-xs text-slate-500 mt-0.5">{description}</p>
                        )}
                    </div>
                    {action && <div className="shrink-0">{action}</div>}
                </div>
            )}
            <div className={noPadding ? "" : "p-4"}>{children}</div>
        </div>
    );
}

interface SectionProps {
    title: string;
    children: ReactNode;
    className?: string;
}

export function Section({ title, children, className = "" }: Readonly<SectionProps>) {
    return (
        <div className={className}>
            <h4 className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2">
                {title}
            </h4>
            {children}
        </div>
    );
}
