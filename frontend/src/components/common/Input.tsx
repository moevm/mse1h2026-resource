import type { InputHTMLAttributes, ReactNode } from "react";
import { cn } from "../../lib/utils/cn";
import { FormField } from "../../shared/components/FormField";

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
        <FormField
            label={label}
            hint={hint}
            error={error}
            icon={icon}
            wrapperClassName={wrapperClassName}
            id={inputId}
        >
            <input
                id={inputId}
                className={cn(
                    "w-full bg-slate-800/80 border rounded-lg px-3.5 py-2 text-sm text-slate-200 h-10",
                    "placeholder:text-slate-500",
                    "transition-all duration-200",
                    "hover:bg-slate-800 hover:border-slate-600",
                    "focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500 focus:bg-slate-800",
                    "disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-slate-800/80",
                    error
                        ? "border-red-500/60 bg-red-500/5 focus:ring-red-500/40 focus:border-red-500"
                        : "border-slate-700/80",
                    icon && "pl-10",
                    className,
                )}
                {...rest}
            />
        </FormField>
    );
}
