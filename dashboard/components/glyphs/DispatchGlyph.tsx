export default function DispatchGlyph({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      className={className}
    >
      {/* Neural network node cluster */}
      <circle cx="12" cy="4" r="2" />
      <circle cx="5" cy="12" r="2" />
      <circle cx="19" cy="12" r="2" />
      <circle cx="8" cy="20" r="2" />
      <circle cx="16" cy="20" r="2" />
      {/* Connections */}
      <line x1="12" y1="6" x2="5" y2="10" />
      <line x1="12" y1="6" x2="19" y2="10" />
      <line x1="5" y1="14" x2="8" y2="18" />
      <line x1="5" y1="14" x2="16" y2="18" />
      <line x1="19" y1="14" x2="8" y2="18" />
      <line x1="19" y1="14" x2="16" y2="18" />
    </svg>
  );
}
