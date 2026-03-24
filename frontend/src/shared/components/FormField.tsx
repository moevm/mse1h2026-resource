import type { ReactNode } from "react";
import { IconExclamation } from "../../components/icons";

interface FormFieldProps {
    label?: string;
    hint?: string;
    error?: string;
    icon?: ReactNode;
    children: ReactNode;
    wrapperClassName?: string;
    id?: string;
}

export function FormField({
    label,
    hint,
    error,
    icon,
    children,
    wrapperClassName = "",
    id,
}: Readonly<FormFieldProps>) {
    const fieldId = id ?? label?.toLowerCase().replaceAll(" ", "-");

    return (
        <div className={wrapperClassName}>
            {label && (
                <label
                    htmlFor={fieldId}
                    className="block text-sm font-medium text-slate-300 mb-2"
                >
                    {label}
                </label>
            )}
            <div className="relative group">
                {icon && (
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-slate-400 transition-colors pointer-events-none">
                        {icon}
                    </span>
                )}
                {children}
            </div>
            {error && (
                <p className="mt-1.5 text-xs text-red-400 flex items-center gap-1">
                    <IconExclamation className="w-3.5 h-3.5" />
                    {error}
                </p>
            )}
            {hint && !error && <p className="mt-1.5 text-xs text-slate-500">{hint}</p>}
        </div>
    );
}
