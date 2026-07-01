"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/plots");
  }, [router]);

  return (
    <div className="min-h-screen bg-[#eef0e8] flex items-center justify-center">
      <div className="w-8 h-8 rounded-full border-4 border-[#2f5d3f] border-t-transparent animate-spin" />
    </div>
  );
}
