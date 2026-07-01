import { Maximize2, Minus, Plus } from "lucide-react";
import {
  createContext,
  type MutableRefObject,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";

import { getIconSizeClass, IconButton } from "@/components/ui/IconButton";

const MIN_SCALE = 0.5;
const MAX_SCALE = 5;
const ZOOM_STEP = 1.25;
const DRAG_THRESHOLD = 4;

const PanZoomContext = createContext(1);

export function usePanZoomScale(): number {
  return useContext(PanZoomContext);
}

interface PanZoomSvgProps {
  viewBox: string;
  className?: string;
  children: ReactNode;
}

interface Transform {
  x: number;
  y: number;
  scale: number;
}

const INITIAL_TRANSFORM: Transform = { x: 0, y: 0, scale: 1 };

function clampScale(scale: number): number {
  return Math.min(MAX_SCALE, Math.max(MIN_SCALE, scale));
}

export function PanZoomSvg({ viewBox, className = "", children }: PanZoomSvgProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [transform, setTransform] = useState<Transform>(INITIAL_TRANSFORM);
  const [isDragging, setIsDragging] = useState(false);
  const suppressClickRef = useRef(false);
  const dragStateRef = useRef<{
    pointerId: number;
    startX: number;
    startY: number;
    originX: number;
    originY: number;
    moved: boolean;
  } | null>(null);

  const screenToSvg = useCallback((clientX: number, clientY: number) => {
    const svg = svgRef.current;
    if (!svg) return { x: 0, y: 0 };

    const point = svg.createSVGPoint();
    point.x = clientX;
    point.y = clientY;
    const ctm = svg.getScreenCTM();
    if (!ctm) return { x: 0, y: 0 };

    const svgPoint = point.matrixTransform(ctm.inverse());
    return { x: svgPoint.x, y: svgPoint.y };
  }, []);

  const zoomAtPoint = useCallback(
    (clientX: number, clientY: number, scaleFn: (currentScale: number) => number) => {
      const svgPoint = screenToSvg(clientX, clientY);
      setTransform((current) => {
        const scale = clampScale(scaleFn(current.scale));
        const ratio = scale / current.scale;
        return {
          scale,
          x: svgPoint.x - (svgPoint.x - current.x) * ratio,
          y: svgPoint.y - (svgPoint.y - current.y) * ratio,
        };
      });
    },
    [screenToSvg],
  );

  const handleWheel = useCallback(
    (event: WheelEvent) => {
      event.preventDefault();
      const direction = event.deltaY > 0 ? -1 : 1;
      const factor = direction > 0 ? ZOOM_STEP : 1 / ZOOM_STEP;
      zoomAtPoint(event.clientX, event.clientY, (scale) => scale * factor);
    },
    [zoomAtPoint],
  );

  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;

    svg.addEventListener("wheel", handleWheel, { passive: false });
    return () => svg.removeEventListener("wheel", handleWheel);
  }, [handleWheel]);

  const handlePointerDown = useCallback((event: React.PointerEvent<SVGSVGElement>) => {
    if (event.button !== 0) return;

    dragStateRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      originX: transform.x,
      originY: transform.y,
      moved: false,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
  }, [transform.x, transform.y]);

  const handlePointerMove = useCallback((event: React.PointerEvent<SVGSVGElement>) => {
    const drag = dragStateRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;

    const dx = event.clientX - drag.startX;
    const dy = event.clientY - drag.startY;
    if (!drag.moved && Math.hypot(dx, dy) < DRAG_THRESHOLD) return;

    drag.moved = true;
    suppressClickRef.current = true;
    setIsDragging(true);

    const start = screenToSvg(drag.startX, drag.startY);
    const current = screenToSvg(event.clientX, event.clientY);

    setTransform((prev) => ({
      ...prev,
      x: drag.originX + (current.x - start.x),
      y: drag.originY + (current.y - start.y),
    }));
  }, [screenToSvg]);

  const endDrag = useCallback((event: React.PointerEvent<SVGSVGElement>) => {
    const drag = dragStateRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;

    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }

    dragStateRef.current = null;
    setIsDragging(false);

    if (drag.moved) {
      window.setTimeout(() => {
        suppressClickRef.current = false;
      }, 0);
    }
  }, []);

  const zoomIn = useCallback(() => {
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    zoomAtPoint(rect.left + rect.width / 2, rect.top + rect.height / 2, (scale) => scale * ZOOM_STEP);
  }, [zoomAtPoint]);

  const zoomOut = useCallback(() => {
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    zoomAtPoint(rect.left + rect.width / 2, rect.top + rect.height / 2, (scale) => scale / ZOOM_STEP);
  }, [zoomAtPoint]);

  const resetView = useCallback(() => {
    setTransform(INITIAL_TRANSFORM);
  }, []);

  return (
    <PanZoomContext.Provider value={transform.scale}>
      <div className="relative h-full w-full overflow-hidden">
        <svg
        ref={svgRef}
        className={`h-full w-full touch-none ${isDragging ? "cursor-grabbing" : "cursor-grab"} ${className}`}
        viewBox={viewBox}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
      >
        <g transform={`translate(${transform.x} ${transform.y}) scale(${transform.scale})`}>
          <PanZoomClickGuard suppressClickRef={suppressClickRef}>{children}</PanZoomClickGuard>
        </g>
      </svg>

      <div className="pointer-events-none absolute inset-x-0 top-2 flex justify-center">
        <p className="rounded-full bg-white/80 px-3 py-1 text-xs text-gray-500 shadow-sm backdrop-blur-sm">
          Scroll to zoom • Drag to pan
        </p>
      </div>

      <div className="absolute right-3 top-3 flex flex-col gap-1 rounded-lg border border-gray-200 bg-white/90 p-1 shadow-sm backdrop-blur-sm">
        <IconButton size="sm" title="Zoom in" aria-label="Zoom in" onClick={zoomIn}>
          <Plus className={getIconSizeClass("sm")} />
        </IconButton>
        <IconButton size="sm" title="Zoom out" aria-label="Zoom out" onClick={zoomOut}>
          <Minus className={getIconSizeClass("sm")} />
        </IconButton>
        <IconButton size="sm" title="Reset view" aria-label="Reset view" onClick={resetView}>
          <Maximize2 className={getIconSizeClass("sm")} />
        </IconButton>
      </div>
      </div>
    </PanZoomContext.Provider>
  );
}

function PanZoomClickGuard({
  children,
  suppressClickRef,
}: {
  children: ReactNode;
  suppressClickRef: MutableRefObject<boolean>;
}) {
  return (
    <g
      onClickCapture={(event) => {
        if (suppressClickRef.current) {
          event.preventDefault();
          event.stopPropagation();
        }
      }}
    >
      {children}
    </g>
  );
}
