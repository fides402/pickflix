// Tiny inline SVG line chart -- avoids pulling in a charting dependency for
// what's just "distance over iteration index".
export default function ConvergenceChart({ iterations }) {
  if (!iterations || iterations.length === 0) {
    return <p className="hint">Nessuna iterazione ancora.</p>;
  }

  const width = 480;
  const height = 160;
  const padding = 24;

  const distances = iterations.map((it) => it.distance);
  const maxD = Math.max(...distances);
  const minD = Math.min(...distances);
  const range = maxD - minD || 1;

  const points = iterations.map((it, i) => {
    const x = padding + (i / Math.max(1, iterations.length - 1)) * (width - 2 * padding);
    const y = height - padding - ((it.distance - minD) / range) * (height - 2 * padding);
    return `${x},${y}`;
  });

  return (
    <div>
      <svg width={width} height={height} className="chart">
        <polyline points={points.join(" ")} fill="none" stroke="#4f9dff" strokeWidth="2" />
      </svg>
      <p className="hint">
        {iterations.length} iterazioni — distanza attuale: {distances[distances.length - 1].toFixed(4)}
      </p>
    </div>
  );
}
