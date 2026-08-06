// Multi-stop color scales for the timeline scrubber — maps a raw sensor value to
// a marker fill color. Ranges are set from the plausible bounds of our seed data
// (see backend/data/build_static_seed.py), not a universal ocean standard.
// Stops go through a pale midpoint rather than a straight 2-color lerp — a direct
// blue->red interpolation passes through a muddy grey-purple in the middle.

type RGB = [number, number, number];

const SCALES: Record<string, { min: number; max: number; stops: RGB[] }> = {
  sst: { min: 26, max: 31, stops: [[46, 134, 193], [238, 244, 244], [214, 81, 45]] }, // cool blue -> pale -> hot coral
  chlorophyll: { min: 0.1, max: 1.2, stops: [[238, 244, 244], [46, 158, 91], [27, 122, 61]] }, // pale -> green -> deep green
};

function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t;
}

export function colorForMetricValue(metric: string, value: number): string {
  const scale = SCALES[metric];
  if (!scale) return "#128F82";
  const t = Math.max(0, Math.min(1, (value - scale.min) / (scale.max - scale.min)));
  const segments = scale.stops.length - 1;
  const segT = t * segments;
  const i = Math.min(segments - 1, Math.floor(segT));
  const localT = segT - i;
  const [r1, g1, b1] = scale.stops[i];
  const [r2, g2, b2] = scale.stops[i + 1];
  const r = Math.round(lerp(r1, r2, localT));
  const g = Math.round(lerp(g1, g2, localT));
  const b = Math.round(lerp(b1, b2, localT));
  return `rgb(${r}, ${g}, ${b})`;
}
