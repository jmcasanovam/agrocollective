"use client";

interface TopbarProps {
  onMenuClick: () => void;
}

export function Topbar({ onMenuClick }: TopbarProps) {
  return (
    <header className="h-14 shrink-0 bg-[#fbfaf6] border-b border-[#e3ddce] flex items-center gap-3 px-4 sticky top-0 z-20 font-sans lg:hidden">
      <button
        onClick={onMenuClick}
        aria-label="Abrir menú"
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-[#3a4a42] hover:bg-[#f0ede4] transition-colors"
      >
        <svg
          width="19"
          height="19"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <line x1="4" x2="20" y1="6" y2="6" />
          <line x1="4" x2="20" y1="12" y2="12" />
          <line x1="4" x2="20" y1="18" y2="18" />
        </svg>
      </button>
      <span className="text-[15px] font-bold text-[#24302a]">AgroCollective</span>
    </header>
  );
}
