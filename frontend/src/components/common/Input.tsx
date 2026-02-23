import type { InputHTMLAttributes, ReactNode } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
    label?: string;
    hint?: string;
    error?: string;
    icon?: ReactNode;
    wrapperClassName?: string;
}

export function Input({
    label,
    hint,
    error,
    icon,
    className = "",
    wrapperClassName = "",
    id,
    ...rest
}: Readonly<InputProps>) {
    const inputId = id ?? label?.toLowerCase().replaceAll(" ", "-");

    return (
        <div className={wrapperClassName}>
            {label && (
                <label
                    htmlFor={inputId}
                    className="block text-xs font-medium text-slate-400 mb-1.5"
                >
                    {label}
                </label>
            )}
            <div className="relative">
                {icon && (
                    <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none">
                        {icon}
                    </span>
                )}
                <input
                    id={inputId}
                    className={[
                        "w-full bg-slate-800 border rounded-lg px-3 py-1.5 text-sm text-slate-200",
                        "placeholder-slate-500 transition-colors",
                        "focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500",
                        "disabled:opacity-50 disabled:cursor-not-allowed",
                        error ? "border-red-600" : "border-slate-700 hover:border-slate-600",
                        icon ? "pl-9" : "",
                        className,
                    ]
                        .filter(Boolean)
                        .join(" ")}
                    {...rest}
                />
            </div>
            {error && <p className="mt-1 text-xs text-red-400">{error}</p>}
            {hint && !error && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
        </div>
    );
}
