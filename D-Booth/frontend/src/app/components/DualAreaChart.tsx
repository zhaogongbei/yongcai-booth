export interface ChartDataItem {
  [key: string]: string | number;
}

export function DualAreaChart({ data, keys, colors, labelKey, height = 110 }: {
  data: ChartDataItem[];
  keys: [string, string];
  colors: [string, string];
  labelKey: string;
  height?: number;
}) {
  const vals0 = data.map(d => d[keys[0]] as number);
  const vals1 = data.map(d => d[keys[1]] as number);
  const max = Math.max(...vals0, ...vals1);
  const w = 500; const h = height - 18;
  const mkPts = (vals: number[]) => vals.map((v, i) => ({ x: (i / (vals.length - 1)) * w, y: h - (v / max) * (h - 6) - 3 }));
  const mkLine = (pts: {x:number;y:number}[]) => pts.map((p,i) => `${i===0?"M":"L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
  const p0 = mkPts(vals0); const p1 = mkPts(vals1);
  const l0 = mkLine(p0); const l1 = mkLine(p1);
  return (
    <svg viewBox={`0 0 ${w} ${height}`} className="w-full" style={{ height }} preserveAspectRatio="none">
      <path d={`${l0} L${w},${h} L0,${h} Z`} fill={colors[0]} fillOpacity={0.12} />
      <path d={`${l1} L${w},${h} L0,${h} Z`} fill={colors[1]} fillOpacity={0.10} />
      <path d={l0} fill="none" stroke={colors[0]} strokeWidth={2} strokeLinejoin="round" />
      <path d={l1} fill="none" stroke={colors[1]} strokeWidth={2} strokeLinejoin="round" />
      {data.map((d, i) => (
        <text key={i} x={(i / (data.length - 1)) * w} y={height - 2} textAnchor="middle" fontSize={10} fill="rgba(255,255,255,0.3)">
          {d[labelKey]}
        </text>
      ))}
    </svg>
  );
}
