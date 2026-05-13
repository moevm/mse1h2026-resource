import { useCallback, useEffect, useRef, useState } from 'react';

interface ResizablePanelsProps {
  children: React.ReactNode[];
  direction?: 'horizontal' | 'vertical';
  initialSizes?: number[];
  minSizes?: number[];
  className?: string;
}

export function ResizablePanels({
  children,
  direction = 'horizontal',
  initialSizes,
  minSizes = [200, 200, 200],
  className = '',
}: ResizablePanelsProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [sizes, setSizes] = useState<number[]>(() => {
    if (initialSizes && initialSizes.length > 0) return initialSizes;
    if (children.length > 0) return children.map(() => 100 / children.length);
    return [];
  });
  const [isDragging, setIsDragging] = useState(false);
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [startPos, setStartPos] = useState(0);
  const [startSizes, setStartSizes] = useState<number[]>([]);

  const handleMouseDown = useCallback(
    (index: number, e: React.MouseEvent) => {
      e.preventDefault();
      setIsDragging(true);
      setDragIndex(index);
      setStartPos(direction === 'horizontal' ? e.clientX : e.clientY);
      setStartSizes([...sizes]);
    },
    [direction, sizes],
  );

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!isDragging || dragIndex === null || !containerRef.current) return;

      const container = containerRef.current;
      const rect = container.getBoundingClientRect();
      const containerSize = direction === 'horizontal' ? rect.width : rect.height;
      const currentPos = direction === 'horizontal' ? e.clientX : e.clientY;
      const delta = currentPos - startPos;
      const deltaPercent = (delta / containerSize) * 100;

      const newSizes = [...startSizes];

      const newSize1 = startSizes[dragIndex] + deltaPercent;
      const newSize2 = startSizes[dragIndex + 1] - deltaPercent;

      const minSize1 = ((minSizes[dragIndex] ?? 100) / containerSize) * 100;
      const minSize2 = ((minSizes[dragIndex + 1] ?? 100) / containerSize) * 100;

      if (newSize1 >= minSize1 && newSize2 >= minSize2) {
        newSizes[dragIndex] = newSize1;
        newSizes[dragIndex + 1] = newSize2;
        setSizes(newSizes);
      }
    },
    [isDragging, dragIndex, startPos, startSizes, direction, minSizes],
  );

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
    setDragIndex(null);
  }, []);

  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = direction === 'horizontal' ? 'col-resize' : 'row-resize';
      document.body.style.userSelect = 'none';
    }
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isDragging, handleMouseMove, handleMouseUp, direction]);

  const isHorizontal = direction === 'horizontal';

  return (
    <div
      ref={containerRef}
      className={`flex ${isHorizontal ? 'flex-row' : 'flex-col'} h-full min-h-0 w-full min-w-0 ${className}`}
    >
      {children.map((child, index) => (
        <div key={index} className="contents">
          <div
            style={{
              [isHorizontal ? 'width' : 'height']: `${sizes[index] ?? 100 / children.length}%`,
              flexShrink: 0,
              overflow: 'hidden',
            }}
            className="flex min-h-0 min-w-0 flex-col"
          >
            {child}
          </div>

          {index < children.length - 1 && (
            <button
              type="button"
              className={`flex-shrink-0 border-0 bg-transparent p-0 ${
                isHorizontal ? 'w-1.5 cursor-col-resize hover:w-2.5' : 'h-1.5 cursor-row-resize hover:h-2.5'
              } bg-slate-700/50 transition-all duration-100 hover:bg-blue-500/50 ${isDragging && dragIndex === index ? 'bg-blue-500' : ''} `}
              onMouseDown={(e) => handleMouseDown(index, e)}
            />
          )}
        </div>
      ))}
    </div>
  );
}
