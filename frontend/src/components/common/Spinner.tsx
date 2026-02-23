interface SpinnerProps {
    size?: "xs" | "sm" | "md" | "lg";
    className?: string;

    label?: string;
}

const sizeMap = { xs: "h-3.5 w-3.5", sm: "h-4 w-4", md: "h-6 w-6", lg: "h-10 w-10" };

export function Spinner({ size = "md", className = "", label }: Readonly<SpinnerProps>) {
    return (
        <div className="flex flex-col items-center gap-2">
            <svg
                className={`animate-spin text-blue-400 ${sizeMap[size]} ${className}`}
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                aria-label="Loading"
            >
                <circle
                    className="opacity-20"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="3"
                />
                <path
                    className="opacity-80"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
            </svg>
            {label && <span className="text-xs text-slate-500 animate-pulse">{label}</span>}
        </div>
    );
}
