import { type ReactNode } from "react";

export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-col lg:flex-row h-screen overflow-y-auto bg-[#eef0e8] font-sans">
      {/* Brand Panel */}
      <div className="flex flex-row lg:flex-col items-center justify-center w-full lg:w-[46%] bg-[#22402e] text-[#eef3ea] py-6 px-4 sm:py-8 lg:p-14 relative overflow-hidden">
        <div className="flex flex-row lg:flex-col items-center gap-3 lg:gap-4 z-10">
          <div className="w-10 h-10 lg:w-14 lg:h-14 rounded-xl bg-[#4f8a5b] flex items-center justify-center shrink-0">
            <svg
              width="22"
              height="22"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#fff"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="lg:w-7 lg:h-7"
            >
              <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z" />
              <path d="M2 21c0-3 1.85-5.36 5.08-6" />
            </svg>
          </div>
          <div className="text-lg lg:text-2xl font-bold tracking-tight">AgroCollective</div>
        </div>
        <div className="hidden lg:block absolute -right-16 -bottom-16 w-72 h-72 rounded-full bg-gradient-to-tr from-[#4f8a5b]/35 to-transparent filter blur-2xl pointer-events-none" />
      </div>

      {/* Form Panel */}
      <div className="flex-1 flex items-center justify-center p-6 sm:p-8 bg-[#eef0e8]">
        <div className="w-full max-w-sm bg-white lg:bg-transparent p-6 sm:p-8 lg:p-0 rounded-2xl lg:rounded-none shadow-md lg:shadow-none border lg:border-none border-[#d9d3c5]/60">
          {children}
        </div>
      </div>
    </div>
  );
}
