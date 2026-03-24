import type { SelectHTMLAttributes, ReactNode } from "react";
import { cn } from "../../lib/utils/cn";
import { FormField } from "../../shared/components/FormField";

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
        <FormField label={label} hint={hint} error={error} wrapperClassName={wrapperClassName} id={selectId}>
            <div className="relative">
                <select
                    id={selectId}
                    className={cn(
                        "w-full bg-slate-800/80 border rounded-lg px-3.5 py-2 pr-10 text-sm text-slate-200 h-10",
                        "transition-all duration-200 cursor-pointer",
                        "hover:bg-slate-800 hover:border-slate-600",
                        "focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500 focus:bg-slate-800",
                        "disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-slate-800/80",
                        "appearance-none",
                        error
                            ? "border-red-500/60 bg-red-500/5 focus:ring-red-500/40 focus:border-red-500"
                            : "border-slate-700/80",
                        className,
                    )}
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
                <span className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-slate-500">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                    </svg>
                </span>
            </div>
        </FormField>
    );
}
