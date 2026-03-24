import type { ComponentType } from "react";
import {
    IconDashboard,
    IconGraph,
    IconMapper,
    IconAgents,
} from "../../components/icons";

interface NavItemBase {
    to: string;
    end: boolean;
    label: string;
    icon: ComponentType<{ className?: string }>;
    badge?: string;
}

export const NAV_ITEMS: NavItemBase[] = [
    { to: "/", end: true, label: "Dashboard", icon: IconDashboard },
    { to: "/graph", end: false, label: "Graph", icon: IconGraph },
    { to: "/mapper", end: false, label: "Mapper", icon: IconMapper },
    { to: "/agents", end: false, label: "Agents", icon: IconAgents },
] as const;

export type NavItem = (typeof NAV_ITEMS)[number];
