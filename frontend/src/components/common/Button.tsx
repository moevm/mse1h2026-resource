import type { ButtonHTMLAttributes, ReactNode } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: "primary" | "secondary" | "ghost" | "danger" | "success";
    size?: "xs" | "sm" | "md" | "lg";
    icon?: ReactNode;
    iconRight?: ReactNode;
    loading?: boolean;
    children?: ReactNode;
}

const base =
    "inline-flex items-center justify-center gap-1.5 rounded-lg font-medium transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-offset-slate-900 disabled:opacity-50 disabled:cursor-not-allowed active:scale-95";

const variants: Record<string, string> = {
    primary:
        "bg-blue-600 hover:bg-blue-500 text-white shadow-sm shadow-blue-900/50 focus:ring-blue-500",
    secondary:
        "bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 hover:border-slate-600 focus:ring-slate-500",
    ghost: "hover:bg-slate-700/60 text-slate-400 hover:text-slate-200 focus:ring-slate-500",
    danger: "bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-800/60 hover:border-red-700 focus:ring-red-500",
    success:
        "bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-800/60 focus:ring-emerald-500",
};

const sizes: Record<string, string> = {
    xs: "px-2 py-0.5 text-[11px]",
    sm: "px-2.5 py-1 text-xs",
    md: "px-3.5 py-1.5 text-sm",
    lg: "px-5 py-2.5 text-sm",
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
                <svg className="animate-spin h-3.5 w-3.5" fill="none" viewBox="0 0 24 24">
                    <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                    />
                    <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                    />
                </svg>
            ) : (
                icon
            )}
            {children}
            {!loading && iconRight}
        </button>
    );
}
