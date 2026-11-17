import React, { useEffect, useRef, useState } from "react";
import { MapContainer, TileLayer, ImageOverlay, useMap } from "react-leaflet";
import type { LatLngBoundsExpression } from "leaflet";
import { SlidersHorizontal } from "lucide-react";
import type { RasterOverlayResponse } from "../api/types";

interface ClippedImageOverlayProps {
  url: string;
  bounds: [[number, number], [number, number]];
  sliderPercent: number;
  opacity?: number;
}

const ClippedImageOverlay: React.FC<ClippedImageOverlayProps> = ({
  url,
  bounds,
  sliderPercent,
  opacity = 1,
}) => {
  const overlayRef = useRef<any>(null);
  const map = useMap();

  const updateClip = () => {
    const el: HTMLElement | undefined = overlayRef.current?.getElement?.();
    if (!el) return;
    // Clip the right side of the "after" image or left side of "after" image:
    // Left side shows BEFORE (underneath), Right side or Left side clipped:
    // Let's make left [0..sliderPercent%] show BEFORE, and [sliderPercent%..100%] show AFTER
    // OR clip AFTER to inset(0 0 0 sliderPercent%) so left is BEFORE and right is AFTER!
    el.style.clipPath = `inset(0 0 0 ${sliderPercent}%)`;
  };

  useEffect(() => {
    updateClip();
  }, [sliderPercent, url, bounds]);

  useEffect(() => {
    map.on("move zoom viewreset", updateClip);
    return () => {
      map.off("move zoom viewreset", updateClip);
    };
  }, [map, sliderPercent]);

  return (
    <ImageOverlay
      ref={overlayRef}
      url={url}
      bounds={bounds as LatLngBoundsExpression}
      opacity={opacity}
      zIndex={450}
      eventHandlers={{
        load: updateClip,
      }}
    />
  );
};

export interface SwipeCompareProps {
  beforeOverlay: RasterOverlayResponse | null;
  afterOverlay: RasterOverlayResponse | null;
  beforeLabel?: string;
  afterLabel?: string;
  center?: [number, number];
  zoom?: number;
  height?: string;
}

export const SwipeCompare: React.FC<SwipeCompareProps> = ({
  beforeOverlay,
  afterOverlay,
  beforeLabel = "Before",
  afterLabel = "After",
  center = [30.75, 79.07],
  zoom = 12,
  height = "420px",
}) => {
  const [slider, setSlider] = useState<number>(50);
  const [opacity, setOpacity] = useState<number>(0.95);

  const bounds = afterOverlay?.bounds ||
    beforeOverlay?.bounds || [
      [30.55, 78.9],
      [30.9, 79.25],
    ];

  return (
    <div className="relative bg-ink-900 border border-white/10 rounded-md overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 bg-ink-950/90 border-b border-white/10 text-xs">
        <div className="flex items-center gap-2">
          <SlidersHorizontal className="w-3.5 h-3.5 text-glacier-400" />
          <span className="font-medium text-slate-200">Swipe Comparison</span>
          <span className="text-slate-400">
            ({beforeLabel} vs. {afterLabel})
          </span>
        </div>
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-1.5 text-slate-400">
            <span>Split: {slider}%</span>
            <input
              type="range"
              min={0}
              max={100}
              value={slider}
              onChange={(e) => setSlider(Number(e.target.value))}
              className="w-28 accent-glacier-400 cursor-pointer"
            />
          </label>
          <label className="flex items-center gap-1.5 text-slate-400">
            <span>Opacity</span>
            <input
              type="range"
              min={0.1}
              max={1}
              step={0.05}
              value={opacity}
              onChange={(e) => setOpacity(Number(e.target.value))}
              className="w-20 accent-glacier-400 cursor-pointer"
            />
          </label>
        </div>
      </div>

      <div className="relative w-full" style={{ height }}>
        <MapContainer
          center={center}
          zoom={zoom}
          bounds={bounds as LatLngBoundsExpression}
          className="w-full h-full z-0"
        >
          <TileLayer
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            attribution="Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics"
          />
          {beforeOverlay && (
            <ImageOverlay
              url={beforeOverlay.image_url}
              bounds={beforeOverlay.bounds as LatLngBoundsExpression}
              opacity={opacity}
              zIndex={400}
            />
          )}
          {afterOverlay && (
            <ClippedImageOverlay
              url={afterOverlay.image_url}
              bounds={afterOverlay.bounds}
              sliderPercent={slider}
              opacity={opacity}
            />
          )}
        </MapContainer>

        {/* Vertical divider indicator */}
        <div
          className="pointer-events-none absolute top-0 bottom-0 z-[500] w-0.5 bg-glacier-400 shadow-[0_0_8px_rgba(94,200,229,0.8)]"
          style={{ left: `${slider}%` }}
        >
          <div className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-6 h-6 rounded-full bg-ink-900 border border-glacier-400 flex items-center justify-center text-[10px] text-glacier-300 shadow">
            ↔
          </div>
        </div>

        {/* Corner Badges */}
        <div className="pointer-events-none absolute top-3 left-12 z-[500] px-2 py-1 rounded bg-ink-950/85 border border-white/15 text-[11px] font-mono text-slate-200">
          ◀ {beforeLabel}
        </div>
        <div className="pointer-events-none absolute top-3 right-3 z-[500] px-2 py-1 rounded bg-ink-950/85 border border-glacier-400/40 text-[11px] font-mono text-glacier-300">
          {afterLabel} ▶
        </div>
      </div>
    </div>
  );
};
