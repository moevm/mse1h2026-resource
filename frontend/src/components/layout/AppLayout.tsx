import type { ReactNode } from "react";
import { Sidebar, Header } from "./Sidebar";

interface AppLayoutProps {
    children: ReactNode;
    headerContent?: ReactNode;
}

export function AppLayout({ children, headerContent }: Readonly<AppLayoutProps>) {
    return (
        <div className="flex h-screen w-screen overflow-hidden bg-slate-950">
            <Sidebar />

            <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
                <Header>{headerContent}</Header>
                <main className="flex-1 overflow-hidden">{children}</main>
            </div>
        </div>
    );
}
