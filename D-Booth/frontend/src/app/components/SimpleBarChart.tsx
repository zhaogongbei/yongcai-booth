import type { ChartDataItem } from "./DualAreaChart";

export function SimpleBarChart({ data, valueKey, labelKey, color = "#8b5cf6", height = 120 }: {
  data: ChartDataItem[];
  valueKey: string;
  labelKey: string;
  color?: string;
  height?: number;
}) {
  const vals = data.map(d => d[valueKey] as number);
  const max = Math.max(...vals);
  const w = 500; const h = height - 18;
  const bw = w / data.length;
  const gap = bw * 0.25;
  return (
    <svg viewBox={`0 0 ${w} ${height}`} className="w-full" style={{ height }} preserveAspectRatio="none">
      {data.map((d, i) => {
        const bh = (Number(d[valueKey]) / max) * (h - 4);
        const x = i * bw + gap / 2;
        return (
          <g key={i}>
            <rect x={x} y={h - bh} width={bw - gap} height={bh} rx={3} fill={color} fillOpacity={0.8} />
            <text x={x + (bw - gap) / 2} y={height - 2} textAnchor="middle" fontSize={10} fill="rgba(255,255,255,0.3)">
              {d[labelKey]}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
