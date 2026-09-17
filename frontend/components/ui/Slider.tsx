"use client";

import { useState } from "react";

// A hand-built range slider — the native input still drives the value (so
// keyboard/touch/accessibility all work for free), we just draw the track
// fill ourselves and pop a value bubble above the thumb while dragging.
export function Slider({
  value,
  min,
  max,
  step = 1,
  onChange,
  formatValue,
  accent = "#23345C",
  disabled = false,
}: {
  value: number;
  min: number;
  max: number;
  step?: number;
  onChange: (v: number) => void;
  formatValue?: (v: number) => string;
  accent?: string;
  disabled?: boolean;
}) {
  const [dragging, setDragging] = useState(false);
  const pct = ((value - min) / (max - min)) * 100;
  const startDrag = () => setDragging(true);
  const endDrag = () => setDragging(false);

  return (
    <div className="relative" style={{ paddingTop: dragging ? 28 : 4 }}>
      {dragging && (
        <div
          className="absolute top-0 -translate-x-1/2 px-2 py-0.5 rounded-md text-[10px] font-bold text-white whitespace-nowrap pointer-events-none transition-opacity"
          style={{ left: `${pct}%`, background: accent }}
        >
          {formatValue ? formatValue(value) : value}
        </div>
      )}
      <div className="relative h-6 flex items-center">
        <div className="absolute inset-x-0 h-1.5 rounded-full" style={{ background: "#E6E2D8" }} />
        <div
          className="absolute h-1.5 rounded-full"
          style={{ width: `${pct}%`, background: disabled ? "#CDC9BE" : accent, transition: dragging ? "none" : "width 0.2s ease" }}
        />
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          disabled={disabled}
          onChange={(e) => onChange(Number(e.target.value))}
          onMouseDown={startDrag}
          onMouseUp={endDrag}
          onTouchStart={startDrag}
          onTouchEnd={endDrag}
          onBlur={endDrag}
          className="slider-input relative w-full cursor-pointer disabled:cursor-not-allowed"
          style={{
            ["--slider-accent" as string]: disabled ? "#CDC9BE" : accent,
            ["--thumb-scale" as string]: dragging ? 1.4 : 1,
          }}
        />
      </div>
    </div>
  );
}
