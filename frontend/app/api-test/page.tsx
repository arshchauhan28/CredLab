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
    <main className="min-h-screen bg-slate-950 p-8 text-white">
      <h1 className="text-2xl font-semibold">
        FastAPI Connection Test
      </h1>

      <div className="mt-6 rounded-xl border border-slate-700 p-5">
        {health.status === "loading" && (
          <p>Checking backend connection...</p>
        )}

        {health.status === "success" && (
          <p className="text-green-400">{health.message}</p>
        )}

        {health.status === "error" && (
          <p className="text-red-400">
            Connection failed: {health.message}
          </p>
        )}
      </div>
    </main>
  );
}