import { useCyContext } from "../../context/CytoscapeContext";
import { Button } from "../common/Button";
import { IconZoomIn, IconZoomOut, IconFit } from "../icons";

export function GraphControls() {
    const { fitGraph, runLayout, zoomIn, zoomOut } = useCyContext();

    return (
        <div className="absolute bottom-4 left-4 z-30 flex items-center gap-0.5 rounded-xl bg-slate-900/95 border border-slate-700/70 p-1 backdrop-blur-md shadow-xl shadow-black/30">
            <Button
                variant="ghost"
                size="sm"
                onClick={zoomIn}
                title="Zoom in"
                icon={<IconZoomIn />}
            />
            <Button
                variant="ghost"
                size="sm"
                onClick={zoomOut}
                title="Zoom out"
                icon={<IconZoomOut />}
            />
            <div className="w-px h-4 bg-slate-700 mx-0.5" />
            <Button
                variant="ghost"
                size="sm"
                onClick={fitGraph}
                title="Fit to screen"
                icon={<IconFit />}
            />
            <div className="w-px h-4 bg-slate-700 mx-0.5" />
            <Button
                variant="ghost"
                size="xs"
                onClick={() => runLayout("cose")}
                title="Force-directed layout"
            >
                Force
            </Button>
            <Button
                variant="ghost"
                size="xs"
                onClick={() => runLayout("circle")}
                title="Circle layout"
            >
                Circle
            </Button>
            <Button variant="ghost" size="xs" onClick={() => runLayout("grid")} title="Grid layout">
                Grid
            </Button>
        </div>
    );
}
