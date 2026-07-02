import { Slider } from "./ui/slider";

export function SliderControl({ label, value, icon: Icon, min = 0, max = 100, onChange }: {
  label: string;
  value: number;
  min?: number;
  max?: number;
  icon?: React.ElementType;
  onChange?: (value: number) => void;
}) {
  const isPositive = value >= 0;
  // Normalize value to 0-100 range for display
  const displayPercent = max > min ? ((value - min) / (max - min)) * 100 : 0;
  return (
    <div className="flex items-center gap-3">
      {Icon && <Icon size={14} className="text-white/40 flex-shrink-0" />}
      <span className="text-xs text-white/60 w-16 flex-shrink-0">{label}</span>
      <Slider
        min={min}
        max={max}
        value={[value]}
        onValueChange={([v]: number[]) => onChange?.(v)}
        className="flex-1 [&_[data-slot=slider-track]]:h-1.5 [&_[data-slot=slider-track]]:bg-white/10 [&_[data-slot=slider-track]]:rounded-full [&_[data-slot=slider-range]]:bg-gradient-to-r [&_[data-slot=slider-range]]:from-violet-500 [&_[data-slot=slider-range]]:to-pink-500 [&_[data-slot=slider-thumb]]:size-3 [&_[data-slot=slider-thumb]]:bg-white [&_[data-slot=slider-thumb]]:border-0 [&_[data-slot=slider-thumb]]:shadow-lg"
        aria-valuemin={min}
        aria-valuemax={max}
        aria-valuenow={value}
        role="slider"
        aria-label={label}
      />
      <span className={`text-xs font-mono w-10 text-right ${isPositive ? "text-violet-400" : "text-pink-400"}`}>
        +{value}
      </span>
    </div>
  );
}
