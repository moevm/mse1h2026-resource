import { cn } from "../../lib/utils/cn";

interface SpinnerProps {
    size?: "xs" | "sm" | "md" | "lg";
    className?: string;
    label?: string;
}

export function Spinner({ size = "md", className, label }: Readonly<SpinnerProps>) {
    const sizeClasses = {
        xs: "h-3 w-3",
        sm: "h-4 w-4",
        md: "h-5 w-5",
        lg: "h-6 w-6",
    };

    const icon = (
        <svg
            className={cn("animate-spin", sizeClasses[size], className)}
            fill="none"
            viewBox="0 0 24 24"
            aria-label={label ?? "Loading"}
        >
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
    );

    if (!label) {
        return icon;
    }

    return (
        <div className="flex items-center gap-2">
            {icon}
            {label && <span className="text-sm text-slate-400">{label}</span>}
        </div>
    );
}
