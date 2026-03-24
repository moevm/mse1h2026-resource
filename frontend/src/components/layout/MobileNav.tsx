import { useState } from "react";
import { NavLink } from "react-router-dom";
import { useGraphStore } from "../../store/graphStore";
import { IconMenu, IconX } from "../icons";
import { NAV_ITEMS } from "../../lib/constants/navigation";
import { STATUS_CONFIG } from "../../lib/constants/status";
import { LogoMark } from "../../shared/components/LogoMark";

export function MobileNav() {
    const [isOpen, setIsOpen] = useState(false);
    const backendStatus = useGraphStore((s) => s.backendStatus);

    return (
        <>
            {/* Hamburger button - visible on mobile only */}
            <button
                onClick={() => setIsOpen(true)}
                className="lg:hidden fixed top-3 left-3 z-50 p-2.5 rounded-xl bg-slate-800/90 backdrop-blur-sm border border-slate-700/60 shadow-lg"
                aria-label="Open menu"
            >
                <IconMenu className="w-5 h-5 text-slate-300" />
            </button>

            {/* Overlay */}
            {isOpen && (
                <button
                    type="button"
                    className="lg:hidden fixed inset-0 z-40 bg-black/60 backdrop-blur-sm animate-fade-in"
                    onClick={() => setIsOpen(false)}
                    aria-label="Close menu overlay"
                />
            )}

            {/* Drawer */}
            <aside
                className={[
                    "lg:hidden fixed top-0 left-0 z-50 h-full w-64 bg-slate-950 border-r border-slate-800/60",
                    "flex flex-col",
                    "transform transition-transform duration-300 ease-out",
                    isOpen ? "translate-x-0" : "-translate-x-full",
                ].join(" ")}
            >
                {/* Header */}
                <div className="flex items-center justify-between h-14 px-4 border-b border-slate-800/60 shrink-0">
                    <div className="flex items-center gap-3">
                        <LogoMark />
                        <div>
                            <p className="text-sm font-bold text-slate-100 leading-tight">
                                Resource Graph
                            </p>
                            <p className="text-[10px] text-slate-600 leading-tight font-medium uppercase tracking-wide">
                                Topology Explorer
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={() => setIsOpen(false)}
                        className="p-1.5 rounded-lg hover:bg-slate-800 transition-colors"
                        aria-label="Close menu"
                    >
                        <IconX className="w-5 h-5 text-slate-400" />
                    </button>
                </div>

                {/* Navigation */}
                <nav className="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto">
                    <p className="px-2 pb-1.5 text-[9px] font-semibold text-slate-700 uppercase tracking-widest select-none">
                        Navigation
                    </p>
                    {NAV_ITEMS.map(({ to, end, label, icon: Icon }) => (
                        <NavLink
                            key={to}
                            to={to}
                            end={end}
                            onClick={() => setIsOpen(false)}
                            className={({ isActive }) =>
                                [
                                    "group relative flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150",
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
                                    <span className="truncate">{label}</span>
                                </>
                            )}
                        </NavLink>
                    ))}
                </nav>

                {/* Status indicator */}
                <div className="border-t border-slate-800/60 px-4 py-3 shrink-0">
                    <div className="flex items-center gap-2">
                        <span
                            className={["h-2 w-2 rounded-full shrink-0", STATUS_CONFIG[backendStatus].color].join(
                                " ",
                            )}
                        />
                        <span className="text-[11px] font-medium text-slate-600">
                            {STATUS_CONFIG[backendStatus].label}
                        </span>
                    </div>
                </div>
            </aside>
        </>
    );
}