export const GLASS_SELECT_OPTION_CLASS_NAME = "bg-slate-900 text-white";

const GLASS_SELECT_BASE_CLASS_NAME = [
  "border border-white/10",
  "bg-white/5",
  "text-white/80",
  "outline-none",
  "transition-colors",
  "focus:border-violet-400/60",
  "focus:bg-slate-900/90",
  "focus:text-white",
  "disabled:cursor-not-allowed",
  "disabled:opacity-50",
].join(" ");

export function getGlassSelectClassName(layoutClassName: string): string {
  return `${GLASS_SELECT_BASE_CLASS_NAME} ${layoutClassName}`.trim();
}
