import type { SelectHTMLAttributes, ReactNode } from "react";

interface SelectOption {
    value: string;
    label: string;
}

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
    label?: string;
    hint?: string;
    error?: string;
    options: SelectOption[];
    placeholder?: string;
    wrapperClassName?: string;
    children?: ReactNode;
}

export function Select({
    label,
    hint,
    error,
    options,
    placeholder,
    className = "",
    wrapperClassName = "",
    id,
    children,
    ...rest
}: Readonly<SelectProps>) {
    const selectId = id ?? label?.toLowerCase().replaceAll(" ", "-");

    return (
        <div className={wrapperClassName}>
            {label && (
                <label
                    htmlFor={selectId}
                    className="block text-xs font-medium text-slate-400 mb-1.5"
                >
                    {label}
                </label>
            )}
            <select
                id={selectId}
                className={[
                    "w-full bg-slate-800 border rounded-lg px-3 py-1.5 text-sm text-slate-200 transition-colors",
                    "focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500",
                    "disabled:opacity-50 disabled:cursor-not-allowed appearance-none",
                    error ? "border-red-600" : "border-slate-700 hover:border-slate-600",
                    className,
                ]
                    .filter(Boolean)
                    .join(" ")}
                {...rest}
            >
                {placeholder && (
                    <option value="" disabled>
                        {placeholder}
                    </option>
                )}
                {children ??
                    options.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                            {opt.label}
                        </option>
                    ))}
            </select>
            {error && <p className="mt-1 text-xs text-red-400">{error}</p>}
            {hint && !error && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
        </div>
    );
}
