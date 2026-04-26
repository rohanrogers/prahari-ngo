export default function CoordinatorGlyph({ className = "w-6 h-6" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
      <circle cx="12" cy="5" r="2" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="5" cy="18" r="2" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="19" cy="18" r="2" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="12" cy="13" r="1" fill="currentColor" />
      <path d="M12 7 L6 17" stroke="currentColor" strokeWidth="1" opacity="0.5" />
      <path d="M12 7 L18 17" stroke="currentColor" strokeWidth="1" opacity="0.5" />
      <path d="M6 18 L18 18" stroke="currentColor" strokeWidth="1" opacity="0.5" />
    </svg>
  );
}
