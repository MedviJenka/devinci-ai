interface Props {
  className?: string;
}

export default function LogoIcon({ className }: Props) {
  return (
    <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
      <rect x="10" y="10" width="80" height="80" stroke="currentColor" strokeOpacity="0.4" strokeWidth="2.5" />
      <circle cx="50" cy="52" r="40" stroke="currentColor" strokeOpacity="0.6" strokeWidth="2.5" />
      <g stroke="currentColor" strokeWidth="4.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M50 30 L50 68" />
        <path d="M50 36 L16 24" />
        <path d="M50 36 L84 24" />
        <path d="M50 36 L14 46" />
        <path d="M50 36 L86 46" />
        <path d="M50 68 L28 90" />
        <path d="M50 68 L72 90" />
        <path d="M50 68 L44 92" />
        <path d="M50 68 L56 92" />
      </g>
      <circle cx="50" cy="18" r="8" fill="currentColor" />
    </svg>
  );
}
