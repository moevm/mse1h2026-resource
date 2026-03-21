interface SpinnerProps {
    size?: "xs" | "sm" | "md" | "lg";
    className?: string;
    label?: string;
}

const sizeMap = {
    xs: "h-4 w-4",
    sm: "h-5 w-5",
    md: "h-8 w-8",
    lg: "h-12 w-12",
};

const strokeMap = {
    xs: 3,
    sm: 3,
    md: 2.5,
    lg: 2,
};

export function Spinner({ size = "md", className = "", label }: Readonly<SpinnerProps>) {
    return (
        <div className="flex flex-col items-center gap-3">
            <div className="relative">
                <svg
                    className={`animate-spin text-blue-500 ${sizeMap[size]} ${className}`}
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
                        strokeWidth={strokeMap[size]}
                    />
                    <path
                        className="opacity-90"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                    />
                </svg>
                {/* Glow effect */}
                <div
                    className={`absolute inset-0 rounded-full bg-blue-500/20 blur-md animate-pulse`}
                    style={{ transform: "scale(0.8)" }}
                />
            </div>
            {label && (
                <span className="text-sm text-slate-400 font-medium">{label}</span>
            )}
        </div>
    );
}
