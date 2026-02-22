import { getNodeColor } from "../../utils/colors";

interface BadgeProps {
    label: string;

    nodeType?: string;

    color?: string;

    dot?: boolean;
    className?: string;
}

export function Badge({
    label,
    nodeType,
    color,
    dot = true,
    className = "",
}: Readonly<BadgeProps>) {
    const bg = color ?? (nodeType ? getNodeColor(nodeType) : "#475569");

    return (
        <span
            className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium leading-none border ${className}`}
            style={{
                backgroundColor: bg + "1a",
                color: bg,
                borderColor: bg + "44",
            }}
        >
            {dot && (
                <span
                    className="h-1.5 w-1.5 rounded-full shrink-0"
                    style={{ backgroundColor: bg }}
                />
            )}
            {label}
        </span>
    );
}
