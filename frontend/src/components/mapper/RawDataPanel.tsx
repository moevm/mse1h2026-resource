import { useState, useRef, useCallback, useMemo } from "react";
import { useDrag } from "react-dnd";
import { useMapperStore } from "../../store/mapperStore";

interface DragItem {
  type: "FIELD";
  path: string;
  value: unknown;
  dataType: string;
}

interface RawDataPanelProps {
  data: Record<string, unknown>;
  chunkId?: string;
  onCreateMapping?: () => void;
}

// Draggable field component
function DraggableField({
  path,
  value,
  dataType,
  children,
}: {
  path: string;
  value: unknown;
  dataType: string;
  children: React.ReactNode;
}) {
  const ref = useRef<HTMLSpanElement>(null);

  const [{ isDragging }, drag] = useDrag<DragItem, unknown, { isDragging: boolean }>(() => ({
    type: "FIELD",
    item: { type: "FIELD", path, value, dataType },
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    }),
  }), [path, value, dataType]);

  drag(ref);

  return (
    <span
      ref={ref}
      className={`cursor-grab active:cursor-grabbing hover:bg-blue-500/20 px-1 rounded transition-colors ${
        isDragging ? "opacity-50 bg-blue-500/30" : ""
      }`}
      title={`Drag to map: ${path}`}
    >
      {children}
    </span>
  );
}

// Get data type for display
function getDataType(value: unknown): string {
  if (value === null) return "null";
  if (Array.isArray(value)) return "array";
  if (typeof value === "object") return "object";
  return typeof value;
}

// Get nested object count
function getNestedCount(value: unknown): number {
  if (Array.isArray(value)) return value.length;
  if (typeof value === "object" && value !== null) return Object.keys(value).length;
  return 0;
}

// Build path segments for breadcrumb
function buildPathSegments(currentPath: string): { segment: string; fullPath: string }[] {
  if (!currentPath) return [];
  const parts = currentPath.split(/[.[\]]/).filter(Boolean);
  const result: { segment: string; fullPath: string }[] = [];
  let acc = "";
  for (const part of parts) {
    if (acc) {
      if (/^\d+$/.test(part)) {
        acc += `[${part}]`;
      } else {
        acc += `.${part}`;
      }
    } else {
      acc = part;
    }
    result.push({ segment: part, fullPath: acc });
  }
  return result;
}

export function RawDataPanel({ data, chunkId, onCreateMapping }: RawDataPanelProps) {
  const { expandedJsonPaths, toggleJsonPath, expandAllPaths, collapseAllPaths } = useMapperStore();
  const [navigationPath, setNavigationPath] = useState<string>("");

  // Get value at current navigation path
  const currentData = useMemo(() => {
    if (!navigationPath) return data;
    const parts = navigationPath.split(/[.[\]]/).filter(Boolean);
    let current: unknown = data;
    for (const part of parts) {
      if (current === null || current === undefined) return null;
      if (/^\d+$/.test(part) && Array.isArray(current)) {
        current = current[parseInt(part)];
      } else if (typeof current === "object") {
        current = (current as Record<string, unknown>)[part];
      } else {
        return null;
      }
    }
    return current;
  }, [data, navigationPath]);

  // Navigate into a key
  const navigateInto = useCallback((key: string) => {
    setNavigationPath((prev) => {
      if (!prev) return key;
      if (/^\d+$/.test(key)) {
        return `${prev}[${key}]`;
      }
      return `${prev}.${key}`;
    });
  }, []);

  // Navigate back to path segment
  const navigateTo = useCallback((path: string) => {
    setNavigationPath(path);
  }, []);

  // Go up one level
  const navigateUp = useCallback(() => {
    setNavigationPath((prev) => {
      if (!prev) return "";
      const lastDot = prev.lastIndexOf(".");
      const lastBracket = prev.lastIndexOf("[");
      const splitIndex = Math.max(lastDot, lastBracket);
      if (splitIndex === -1) return "";
      if (lastBracket > lastDot) {
        return prev.slice(0, lastBracket);
      }
      return prev.slice(0, splitIndex);
    });
  }, []);

  const renderValue = (
    value: unknown,
    path: string,
    depth: number = 0
  ): React.ReactNode => {
    const indent = depth * 12;
    const dataType = getDataType(value);

    if (value === null) {
      return (
        <DraggableField path={path} value={value} dataType={dataType}>
          <span className="text-slate-500 italic">null</span>
        </DraggableField>
      );
    }

    if (typeof value === "boolean") {
      return (
        <DraggableField path={path} value={value} dataType={dataType}>
          <span className="text-purple-400">{value.toString()}</span>
        </DraggableField>
      );
    }

    if (typeof value === "number") {
      return (
        <DraggableField path={path} value={value} dataType={dataType}>
          <span className="text-blue-400">{value}</span>
        </DraggableField>
      );
    }

    if (typeof value === "string") {
      const truncated = value.length > 60 ? value.slice(0, 60) + "..." : value;
      return (
        <DraggableField path={path} value={value} dataType={dataType}>
          <span className="text-green-400" title={value}>"{truncated}"</span>
        </DraggableField>
      );
    }

    if (Array.isArray(value)) {
      const isExpanded = expandedJsonPaths.has(path);
      const count = value.length;
      return (
        <div>
          <span
            className="cursor-pointer text-slate-400 hover:text-slate-300 select-none"
            onClick={() => toggleJsonPath(path)}
          >
            {isExpanded ? "▼" : "▶"} <span className="text-slate-500">[{count}]</span>
          </span>
          {isExpanded && (
            <div className="border-l-2 border-slate-700 ml-2 pl-2 mt-1">
              {value.map((item, index) => (
                <div key={index} style={{ marginLeft: indent }}>
                  <span className="text-slate-500 mr-1">{index}:</span>
                  {renderValue(item, `${path}[${index}]`, depth + 1)}
                </div>
              ))}
            </div>
          )}
        </div>
      );
    }

    if (typeof value === "object" && value !== null) {
      const isExpanded = expandedJsonPaths.has(path);
      const entries = Object.entries(value as Record<string, unknown>);
      return (
        <div>
          <span
            className="cursor-pointer text-slate-400 hover:text-slate-300 select-none"
            onClick={() => toggleJsonPath(path)}
          >
            {isExpanded ? "▼" : "▶"} <span className="text-slate-500">{"{"}{entries.length}{"}"}</span>
          </span>
          {isExpanded && (
            <div className="border-l-2 border-slate-700 ml-2 pl-2 mt-1">
              {entries.map(([key, val]) => (
                <div key={key} style={{ marginLeft: indent }} className="py-0.5">
                  <DraggableField
                    path={path ? `${path}.${key}` : key}
                    value={val}
                    dataType={getDataType(val)}
                  >
                    <span className="text-amber-400 font-medium hover:text-amber-300">
                      {key}:
                    </span>
                  </DraggableField>{" "}
                  {renderValue(val, path ? `${path}.${key}` : key, depth + 1)}
                </div>
              ))}
            </div>
          )}
        </div>
      );
    }

    return <span className="text-slate-400">{String(value)}</span>;
  };

  // Render navigation item with click-to-navigate
  const renderNavigationItem = (
    key: string,
    value: unknown,
    path: string
  ): React.ReactNode => {
    const dataType = getDataType(value);
    const isObject = dataType === "object" || dataType === "array";
    const nestedCount = getNestedCount(value);

    return (
      <div
        key={key}
        className="group flex items-center gap-2 py-1.5 px-2 hover:bg-slate-700/30 rounded cursor-pointer border border-transparent hover:border-slate-600/50"
        onClick={() => isObject && navigateInto(key)}
      >
        <DraggableField path={path} value={value} dataType={dataType}>
          <span className="text-amber-400 font-medium group-hover:text-amber-300">
            {key}
          </span>
        </DraggableField>
        <span className="text-slate-600">:</span>
        {dataType === "object" && (
          <>
            <span className="text-slate-500 text-xs">{"{}"}</span>
            <span className="text-slate-600 text-xs">{nestedCount}</span>
            <span className="text-blue-400 text-xs ml-auto opacity-0 group-hover:opacity-100">
              → enter
            </span>
          </>
        )}
        {dataType === "array" && (
          <>
            <span className="text-slate-500 text-xs">[]</span>
            <span className="text-slate-600 text-xs">{nestedCount}</span>
            <span className="text-blue-400 text-xs ml-auto opacity-0 group-hover:opacity-100">
              → enter
            </span>
          </>
        )}
        {dataType === "string" && typeof value === "string" && (
          <span className="text-green-400 text-xs truncate max-w-[150px]">
            "{value.length > 30 ? value.slice(0, 30) + "..." : value}"
          </span>
        )}
        {dataType === "number" && typeof value === "number" && (
          <span className="text-blue-400 text-xs">{value}</span>
        )}
        {dataType === "boolean" && (
          <span className="text-purple-400 text-xs">{value ? "true" : "false"}</span>
        )}
        {dataType === "null" && (
          <span className="text-slate-500 text-xs italic">null</span>
        )}
      </div>
    );
  };

  // Current level data
  const currentEntries = useMemo(() => {
    if (currentData === null || currentData === undefined) return [];
    if (Array.isArray(currentData)) {
      return currentData.map((item, index) => [String(index), item] as [string, unknown]);
    }
    if (typeof currentData === "object") {
      return Object.entries(currentData as Record<string, unknown>);
    }
    return [];
  }, [currentData]);

  const pathSegments = buildPathSegments(navigationPath);

  return (
    <div className="h-full flex flex-col">
      {/* Toolbar */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-slate-700/50 bg-slate-800/30 shrink-0">
        <span className="text-xs text-slate-500">Drag fields to schema →</span>
        <div className="flex-1" />
        {chunkId && onCreateMapping && (
          <button
            onClick={onCreateMapping}
            className="text-xs bg-emerald-600/80 hover:bg-emerald-700 text-white px-2 py-0.5 rounded"
          >
            + Create Mapping
          </button>
        )}
        <button
          onClick={expandAllPaths}
          className="text-xs text-slate-500 hover:text-slate-400 px-2 py-0.5 rounded hover:bg-slate-700/50"
        >
          + Expand All
        </button>
        <button
          onClick={collapseAllPaths}
          className="text-xs text-slate-500 hover:text-slate-400 px-2 py-0.5 rounded hover:bg-slate-700/50"
        >
          - Collapse All
        </button>
      </div>

      {/* Breadcrumb Navigation */}
      {navigationPath && (
        <div className="flex items-center gap-1 px-3 py-2 bg-slate-800/50 border-b border-slate-700/50 text-xs overflow-x-auto shrink-0">
          <button
            onClick={() => setNavigationPath("")}
            className="text-blue-400 hover:text-blue-300"
          >
            root
          </button>
          {pathSegments.map((seg, i) => (
            <span key={seg.fullPath} className="flex items-center gap-1">
              <span className="text-slate-600">/</span>
              <button
                onClick={() => navigateTo(seg.fullPath)}
                className={`hover:text-slate-200 ${
                  i === pathSegments.length - 1 ? "text-slate-200" : "text-slate-400"
                }`}
              >
                {seg.segment}
              </button>
            </span>
          ))}
          <button
            onClick={navigateUp}
            className="ml-2 text-slate-500 hover:text-slate-400 px-1.5 py-0.5 bg-slate-700/50 rounded"
          >
            ↑ Up
          </button>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {navigationPath ? (
          // Navigation mode - show items as clickable cards
          <div className="p-2 space-y-0.5">
            {currentEntries.map(([key, value]) =>
              renderNavigationItem(key, value, navigationPath ? `${navigationPath}.${key}` : key)
            )}
            {currentEntries.length === 0 && (
              <div className="text-slate-500 text-sm text-center py-4">
                Empty object
              </div>
            )}
          </div>
        ) : (
          // Tree mode - show full expanded tree
          <div className="p-3 font-mono text-sm">
            {renderValue(data, "", 0)}
          </div>
        )}
      </div>

      {/* Footer with context */}
      <div className="px-3 py-1.5 bg-slate-800/30 border-t border-slate-700/50 text-xs text-slate-500 shrink-0 flex items-center gap-4">
        <span>
          {navigationPath ? (
            <>Viewing: <code className="text-slate-400">{navigationPath}</code></>
          ) : (
            "Root view"
          )}
        </span>
        <span className="text-slate-600">•</span>
        <span>
          {currentEntries.length} {currentEntries.length === 1 ? "field" : "fields"}
        </span>
        {navigationPath && (
          <>
            <span className="text-slate-600">•</span>
            <button
              onClick={() => setNavigationPath("")}
              className="text-blue-400 hover:text-blue-300"
            >
              Back to root
            </button>
          </>
        )}
      </div>
    </div>
  );
}
