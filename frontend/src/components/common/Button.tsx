import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Spinner } from "../../shared/components/Spinner";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: "primary" | "secondary" | "ghost" | "danger" | "success";
    size?: "xs" | "sm" | "md" | "lg";
    icon?: ReactNode;
    iconRight?: ReactNode;
    loading?: boolean;
    children?: ReactNode;
}

const base =
    "inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-all duration-200 ease-out focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none active:scale-[0.97]";

const variants: Record<string, string> = {
    primary:
        "bg-blue-600 hover:bg-blue-500 text-white shadow-md shadow-blue-900/40 hover:shadow-lg hover:shadow-blue-900/50 focus-visible:ring-blue-500",
    secondary:
        "bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700/80 hover:border-slate-600 shadow-sm focus-visible:ring-slate-500",
    ghost:
        "hover:bg-slate-800/80 text-slate-400 hover:text-slate-200 focus-visible:ring-slate-500",
    danger:
        "bg-red-500/15 hover:bg-red-500/25 text-red-400 hover:text-red-300 border border-red-700/50 hover:border-red-600/60 focus-visible:ring-red-500",
    success:
        "bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-400 hover:text-emerald-300 border border-emerald-700/50 hover:border-emerald-600/60 focus-visible:ring-emerald-500",
};

const sizes: Record<string, string> = {
    xs: "px-2.5 py-1 text-xs min-h-[28px]",
    sm: "px-3 py-1.5 text-xs min-h-[32px]",
    md: "px-4 py-2 text-sm min-h-[36px]",
    lg: "px-5 py-2.5 text-sm min-h-[44px]",
};

export function Button({
    variant = "secondary",
    size = "md",
    icon,
    iconRight,
    loading = false,
    children,
    className = "",
    disabled,
    ...rest
}: Readonly<ButtonProps>) {
    return (
        <button
            className={`${base} ${variants[variant]} ${sizes[size]} ${className}`}
            disabled={disabled || loading}
            {...rest}
        >
            {loading ? (
                <Spinner size="sm" className="h-4 w-4" />
            ) : (
                icon
            )}
            {children}
            {!loading && iconRight}
        </button>
    );
}
