import type { ReactNode } from "react";

interface CardProps {
    title?: string;
    description?: string;
    action?: ReactNode;
    children: ReactNode;
    className?: string;
    noPadding?: boolean;
    interactive?: boolean;
}

export function Card({
    title,
    description,
    action,
    children,
    className = "",
    noPadding = false,
    interactive = false,
}: Readonly<CardProps>) {
    const hasMeta = title != null || description != null || action != null;

    return (
        <div
            className={[
                "rounded-xl bg-slate-900/80 border border-slate-800/80 overflow-hidden",
                "shadow-lg shadow-slate-950/50",
                interactive && "hover:border-slate-700/80 hover:bg-slate-900 transition-all duration-200 cursor-pointer",
                className,
            ].filter(Boolean).join(" ")}
        >
            {hasMeta && (
                <div className="flex items-start justify-between gap-4 px-5 pt-4 pb-3 border-b border-slate-800/60">
                    <div className="min-w-0">
                        {title && (
                            <h2 className="text-sm font-semibold text-slate-100 leading-snug">
                                {title}
                            </h2>
                        )}
                        {description && (
                            <p className="text-xs text-slate-400 mt-1">{description}</p>
                        )}
                    </div>
                    {action && <div className="shrink-0">{action}</div>}
                </div>
            )}
            <div className={noPadding ? "" : "p-5"}>{children}</div>
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
            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">
                {title}
            </h4>
            {children}
        </div>
    );
}
