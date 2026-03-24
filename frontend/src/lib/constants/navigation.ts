import type { ComponentType } from "react";
import {
    IconDashboard,
    IconGraph,
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
    { to: "/agents", end: false, label: "Agents", icon: IconAgents },
] as const;

export type NavItem = (typeof NAV_ITEMS)[number];
