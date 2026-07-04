"use client";

interface AlertPopupProps {
  title: string;
  message: string;
  onClose: () => void;
}

export function AlertPopup({ title, message, onClose }: AlertPopupProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[rgba(22,34,26,0.45)] p-6">
      <div className="relative w-[420px] max-w-[92vw] bg-white rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.22)] p-[26px]">
        <button
          onClick={onClose}
          aria-label="Cerrar"
          className="absolute top-[18px] right-[18px] w-[30px] h-[30px] rounded-lg flex items-center justify-center cursor-pointer bg-transparent border-none text-[#8a978d] hover:bg-[#f0ede4] hover:text-[#3a4a42] transition-colors"
        >
          <svg
            width="17"
            height="17"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M18 6 6 18" />
            <path d="m6 6 12 12" />
          </svg>
        </button>

        <h2 className="text-[17px] font-bold text-[#24302a] m-0 mb-2 pr-6">{title}</h2>
        <p className="text-[13px] text-[#6b7a70] m-0">{message}</p>

        <button
          onClick={onClose}
          className="mt-5 w-full h-9 rounded-lg text-[13px] font-semibold text-white bg-[#2f5d3f] hover:bg-[#264b33] transition-colors"
        >
          Entendido
        </button>
      </div>
    </div>
  );
}
