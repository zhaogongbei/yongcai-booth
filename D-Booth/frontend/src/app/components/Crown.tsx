export function Crown({ size = 16, className = "" }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M2 19l2-9 5 4 3-7 3 7 5-4 2 9H2zm2-2h16l-1-5.5-4 3.2-3-7-3 7-4-3.2L4 17z" />
    </svg>
  );
}
