import { getNodeColor } from "../../utils/colors";

interface BadgeProps {
    label: string;
    nodeType?: string;
    color?: string;
    dot?: boolean;
    size?: "sm" | "md";
    className?: string;
}

export function Badge({
    label,
    nodeType,
    color,
    dot = true,
    size = "sm",
    className = "",
}: Readonly<BadgeProps>) {
    const bg = color ?? (nodeType ? getNodeColor(nodeType) : "#64748b");

    const sizeClasses = {
        sm: "px-2 py-1 text-xs gap-1.5",
        md: "px-2.5 py-1.5 text-xs gap-2",
    };

    const dotSizes = {
        sm: "h-2 w-2",
        md: "h-2.5 w-2.5",
    };

    return (
        <span
            className={[
                "inline-flex items-center rounded-full font-medium leading-none border",
                "transition-all duration-150",
                sizeClasses[size],
                className,
            ].join(" ")}
            style={{
                backgroundColor: bg + "20",
                color: bg,
                borderColor: bg + "40",
            }}
        >
            {dot && (
                <span
                    className={`${dotSizes[size]} rounded-full shrink-0 shadow-sm`}
                    style={{
                        backgroundColor: bg,
                        boxShadow: `0 0 6px ${bg}60`,
                    }}
                />
            )}
            {label}
        </span>
    );
}
