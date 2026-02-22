import type { ReactNode, ComponentType } from "react";
import { NavLink } from "react-router-dom";
import { useUiStore } from "../../store/uiStore";
import { useGraphStore } from "../../store/graphStore";
import { IconDashboard, IconGraph, IconAgents, IconChevronLeft } from "../icons";

interface NavItem {
    to: string;
    end: boolean;
    label: string;
    icon: ComponentType<{ className?: string }>;
    badge?: string;
}

const NAV_ITEMS: NavItem[] = [
    { to: "/", end: true, label: "Dashboard", icon: IconDashboard },
    { to: "/graph", end: false, label: "Graph", icon: IconGraph },
    { to: "/agents", end: false, label: "Agents", icon: IconAgents },
];

const STATUS_COLOR = {
    connected: "bg-emerald-500",
    disconnected: "bg-red-500",
    checking: "bg-amber-500 animate-pulse",
} as const;

const STATUS_LABEL = {
    connected: "Connected",
    disconnected: "Disconnected",
    checking: "Checking…",
} as const;

export function Sidebar() {
    const collapsed = useUiStore((s) => s.sidebarCollapsed);
    const toggleSidebar = useUiStore((s) => s.toggleSidebar);
    const backendStatus = useGraphStore((s) => s.backendStatus);

    return (
        <aside
            className={[
                "relative flex flex-col shrink-0 bg-slate-950 border-r border-slate-800/60",
                "transition-[width] duration-300 ease-in-out overflow-x-hidden",
                collapsed ? "w-52" : "w-56",
            ].join(" ")}
        >
            <div
                className={[
                    "flex items-center h-14 border-b border-slate-800/60 shrink-0 select-none",
                    collapsed ? "justify-center" : "gap-3 px-4",
                ].join(" ")}
            >
                <LogoMark />
                {!collapsed && (
                    <div className="min-w-0 overflow-hidden">
                        <p className="text-sm font-bold text-slate-100 truncate leading-tight tracking-tight">
                            Resource Graph
                        </p>
                        <p className="text-[10px] text-slate-600 truncate leading-tight font-medium tracking-wide uppercase">
                            Topology Explorer
                        </p>
                    </div>
                )}
            </div>

            <nav className="flex-1 py-3 space-y-0.5 px-2">
                {!collapsed && (
                    <p className="px-2 pb-1.5 text-[9px] font-semibold text-slate-700 uppercase tracking-widest select-none">
                        Navigation
                    </p>
                )}
                {NAV_ITEMS.map(({ to, end, label, icon: Icon, badge }) => (
                    <NavLink
                        key={to}
                        to={to}
                        end={end}
                        title={collapsed ? label : undefined}
                        className={({ isActive }) =>
                            [
                                "group relative flex items-center gap-3 rounded-lg py-2 text-sm font-medium transition-all duration-150 select-none",
                                collapsed ? "justify-center px-0" : "px-3",
                                isActive
                                    ? "bg-blue-600/12 text-blue-400"
                                    : "text-slate-500 hover:text-slate-200 hover:bg-slate-800/60",
                            ].join(" ")
                        }
                    >
                        {({ isActive }) => (
                            <>
                                {isActive && (
                                    <span className="absolute left-0 top-1/2 -translate-y-1/2 h-4 w-0.5 rounded-full bg-blue-400" />
                                )}
                                <Icon
                                    className={[
                                        "w-4.5 h-4.5 shrink-0 transition-colors",
                                        isActive
                                            ? "text-blue-400"
                                            : "text-slate-500 group-hover:text-slate-300",
                                    ].join(" ")}
                                />
                                {!collapsed && (
                                    <>
                                        <span className="truncate whitespace-nowrap flex-1">
                                            {label}
                                        </span>
                                        {badge && (
                                            <span className="text-[10px] leading-none font-mono bg-slate-800 text-slate-500 rounded px-1 py-0.5">
                                                {badge}
                                            </span>
                                        )}
                                    </>
                                )}
                            </>
                        )}
                    </NavLink>
                ))}
            </nav>

            <div
                className={[
                    "border-t border-slate-800/60 shrink-0 flex items-center gap-2",
                    collapsed ? "justify-center py-2.5" : "px-4 py-2.5",
                ].join(" ")}
                title={collapsed ? STATUS_LABEL[backendStatus] : undefined}
            >
                <span
                    className={["h-2 w-2 rounded-full shrink-0", STATUS_COLOR[backendStatus]].join(
                        " ",
                    )}
                />
                {!collapsed && (
                    <span className="text-[11px] font-medium text-slate-600 truncate">
                        {STATUS_LABEL[backendStatus]}
                    </span>
                )}
            </div>

            <button
                onClick={toggleSidebar}
                title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
                aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
                className="flex items-center justify-center h-9 w-full border-t border-slate-800/60 text-slate-700 hover:text-slate-400 hover:bg-slate-800/30 transition-colors shrink-0"
            >
                <IconChevronLeft
                    className={[
                        "w-3.5 h-3.5 transition-transform duration-300",
                        collapsed ? "rotate-180" : "",
                    ].join(" ")}
                />
            </button>
        </aside>
    );
}

function LogoMark() {
    return (
        <div className="h-8 w-8 rounded-xl bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center text-white font-extrabold text-xs shrink-0 shadow-lg shadow-blue-900/50 tracking-tight select-none">
            RG
        </div>
    );
}

interface HeaderProps {
    children?: ReactNode;
}

export function Header({ children }: Readonly<HeaderProps>) {
    return (
        <header className="flex items-center gap-3 px-5 h-14 bg-slate-950/90 backdrop-blur-md border-b border-slate-800/60 shrink-0">
            {children}
        </header>
    );
}
