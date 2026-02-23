import { createContext, useContext, useRef, type ReactNode, type RefObject } from "react";
import { useCytoscape } from "../hooks/useCytoscape";

interface CyContextValue {
    containerRef: RefObject<HTMLDivElement | null>;
    fitGraph: () => void;
    runLayout: (name?: string) => void;
    zoomIn: () => void;
    zoomOut: () => void;
    centerOn: (nodeId: string) => void;
}

const CyContext = createContext<CyContextValue | null>(null);

export function CytoscapeProvider({ children }: Readonly<{ children: ReactNode }>) {
    const containerRef = useRef<HTMLDivElement>(null);
    const actions = useCytoscape(containerRef);

    return <CyContext.Provider value={{ containerRef, ...actions }}>{children}</CyContext.Provider>;
}

export function useCyContext(): CyContextValue {
    const ctx = useContext(CyContext);
    if (!ctx) throw new Error("useCyContext must be used inside CytoscapeProvider");
    return ctx;
}
