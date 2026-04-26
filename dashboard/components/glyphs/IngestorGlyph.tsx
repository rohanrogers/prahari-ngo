export default function IngestorGlyph({ className = "w-6 h-6" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
      <path d="M4 4 L12 14 L20 4" stroke="currentColor" strokeWidth="1.5" />
      <path d="M12 14 L12 21" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="6" cy="3" r="1" fill="currentColor" />
      <circle cx="12" cy="3" r="1" fill="currentColor" />
      <circle cx="18" cy="3" r="1" fill="currentColor" />
    </svg>
  );
}
