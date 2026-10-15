"use client";

import { useEffect, useState } from "react";
import { checkApiHealth } from "../../lib/api/health";

type HealthState =
  | { status: "loading" }
  | { status: "success"; message: string }
  | { status: "error"; message: string };

export default function ApiTestPage() {
  const [health, setHealth] = useState<HealthState>({
    status: "loading",
  });

  useEffect(() => {
    let active = true;

    checkApiHealth()
      .then((result) => {
        if (active) {
          setHealth({
            status: "success",
            message: `Backend status: ${result.status}`,
          });
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setHealth({
            status: "error",
            message:
              error instanceof Error
                ? error.message
                : "Unable to connect to the backend.",
          });
        }
      });

    return () => {
      active = false;
    };
  }, []);

  return (
    <main className="min-h-screen bg-[#101010] p-8 text-[#F7F4EF]">
      <h1 className="text-2xl font-extrabold tracking-tight">
        FastAPI Connection Test
      </h1>
      <p className="mt-1 text-xs text-[#A5A29C]">
        CredLab backend connectivity verification
      </p>

      <div className="mt-6 rounded-2xl border border-[#353535] bg-[#1B1B1B] p-6 max-w-lg">
        {health.status === "loading" && (
          <p className="text-xs font-semibold text-[#A5A29C]">Checking backend connection...</p>
        )}

        {health.status === "success" && (
          <p className="text-xs font-mono font-bold text-emerald-400">{health.message}</p>
        )}

        {health.status === "error" && (
          <p className="text-xs font-mono font-bold text-rose-400">
            Connection failed: {health.message}
          </p>
        )}
      </div>
    </main>
  );
}