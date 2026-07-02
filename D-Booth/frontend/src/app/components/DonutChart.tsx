export function DonutChart({ data, colors, size = 140 }: { data: {name:string;value:number}[]; colors: string[]; size?: number }) {
  const total = data.reduce((s, d) => s + d.value, 0);
  const r = 30; const R = 45; const cx = size / 2; const cy = size / 2 - 10;
  let angle = -Math.PI / 2;
  const slices = data.map((d, i) => {
    const sweep = (d.value / total) * 2 * Math.PI;
    const x1 = cx + R * Math.cos(angle); const y1 = cy + R * Math.sin(angle);
    const x2 = cx + R * Math.cos(angle + sweep); const y2 = cy + R * Math.sin(angle + sweep);
    const xi1 = cx + r * Math.cos(angle); const yi1 = cy + r * Math.sin(angle);
    const xi2 = cx + r * Math.cos(angle + sweep); const yi2 = cy + r * Math.sin(angle + sweep);
    const large = sweep > Math.PI ? 1 : 0;
    const path = `M${x1.toFixed(2)},${y1.toFixed(2)} A${R},${R} 0 ${large},1 ${x2.toFixed(2)},${y2.toFixed(2)} L${xi2.toFixed(2)},${yi2.toFixed(2)} A${r},${r} 0 ${large},0 ${xi1.toFixed(2)},${yi1.toFixed(2)} Z`;
    angle += sweep;
    return { path, color: colors[i], name: d.name, value: d.value };
  });
  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="w-full" style={{ height: size }}>
      {slices.map((s, i) => <path key={s.name} d={s.path} fill={s.color} fillOpacity={0.9} />)}
    </svg>
  );
}
