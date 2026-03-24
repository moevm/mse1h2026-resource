import { useCyContext } from "../../context/CytoscapeContext";
import { useGraphUiStore } from "../../features/graph/store";
import { Button } from "../common/Button";
import { IconZoomIn, IconZoomOut, IconFit } from "../icons";

export function GraphControls() {
    const { fitGraph, runLayout, zoomIn, zoomOut, centerOn } = useCyContext();
    const selectedNodeId = useGraphUiStore((s) => s.selectedNodeId);
    const clearVisualFocus = useGraphUiStore((s) => s.clearVisualFocus);

    return (
        <div className="absolute bottom-5 left-5 z-30 flex items-center gap-1 rounded-xl bg-slate-900/95 border border-slate-700/70 p-1.5 backdrop-blur-md shadow-2xl shadow-black/40 animate-fade-in">
            {/* Zoom controls */}
            <Button
                variant="ghost"
                size="sm"
                onClick={zoomIn}
                title="Zoom in (Alt + +)"
                icon={<IconZoomIn className="w-4 h-4" />}
                className="hover:bg-slate-800"
            />
            <Button
                variant="ghost"
                size="sm"
                onClick={zoomOut}
                title="Zoom out (Alt + -)"
                icon={<IconZoomOut className="w-4 h-4" />}
                className="hover:bg-slate-800"
            />

            <div className="w-px h-5 bg-slate-700/60 mx-1" />

            <Button
                variant="ghost"
                size="sm"
                onClick={fitGraph}
                title="Fit to screen (Alt + 0)"
                icon={<IconFit className="w-4 h-4" />}
                className="hover:bg-slate-800"
            />

            <div className="w-px h-5 bg-slate-700/60 mx-1" />

            {/* Layout controls */}
            <Button
                variant="ghost"
                size="sm"
                onClick={() => runLayout("cose")}
                title="Force-directed layout"
                className="hover:bg-slate-800 font-medium"
            >
                Force
            </Button>
            <Button
                variant="ghost"
                size="sm"
                onClick={() => runLayout("circle")}
                title="Circle layout"
                className="hover:bg-slate-800 font-medium"
            >
                Circle
            </Button>
            <Button
                variant="ghost"
                size="sm"
                onClick={() => runLayout("grid")}
                title="Grid layout"
                className="hover:bg-slate-800 font-medium"
            >
                Grid
            </Button>

            <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                    if (selectedNodeId) centerOn(selectedNodeId);
                }}
                title="Center selected node"
                disabled={!selectedNodeId}
                className="hover:bg-slate-800 font-medium"
            >
                Center
            </Button>
            <Button
                variant="ghost"
                size="sm"
                onClick={clearVisualFocus}
                title="Clear current focus and path highlights"
                className="hover:bg-slate-800 font-medium"
            >
                Clear
            </Button>
        </div>
    );
}
