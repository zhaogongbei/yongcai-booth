import type React from "react";

type GlowBtnProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "accent" | "ghost" | "outline";
  size?: "sm" | "md" | "lg";
};

export function GlowBtn({
  children,
  variant = "primary",
  className = "",
  size = "md",
  type = "button",
  disabled,
  ...buttonProps
}: GlowBtnProps) {
  const variants: Record<string, string> = {
    primary: "bg-gradient-to-r from-violet-600 to-violet-500 hover:from-violet-500 hover:to-violet-400 text-white shadow-[0_0_20px_rgba(139,92,246,0.4)]",
    accent: "bg-gradient-to-r from-pink-600 to-pink-500 hover:from-pink-500 hover:to-pink-400 text-white shadow-[0_0_20px_rgba(236,72,153,0.4)]",
    ghost: "bg-white/5 hover:bg-white/10 text-white/80 border border-white/10",
    outline: "border border-violet-500/40 hover:border-violet-500/80 text-violet-400 hover:bg-violet-500/10",
  };
  const sizes: Record<string, string> = {
    sm: "px-3 py-1.5 text-xs rounded-lg",
    md: "px-4 py-2 text-sm rounded-xl",
    lg: "px-6 py-3 text-base rounded-2xl",
  };
  return (
    <button
      {...buttonProps}
      type={type}
      disabled={disabled}
      className={`inline-flex items-center gap-2 font-medium transition-all duration-200 ${disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer"} ${variants[variant]} ${sizes[size]} ${className}`}
    >
      {children}
    </button>
  );
}
