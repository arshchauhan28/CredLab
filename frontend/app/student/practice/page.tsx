"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function PracticeRedirectPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/student/dashboard?tab=practice-arena");
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#101010] text-xs text-[#A5A29C]">
      <div className="flex items-center gap-3">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-[#FF6B2C] border-t-transparent" />
        <span>Navigating to Practice Arena...</span>
      </div>
    </div>
  );
}
