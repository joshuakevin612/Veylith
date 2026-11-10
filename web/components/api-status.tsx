"use client";

import { useEffect, useState } from "react";

import type { components } from "@/lib/api/schema";

type Health = components["schemas"]["Health"];
type State = "checking" | "ok" | "down";

/** Milestone 0 smoke test: proves the web app can reach the API through the /api proxy. */
export function ApiStatus() {
  const [state, setState] = useState<State>("checking");

  useEffect(() => {
    fetch("/api/health")
      .then((res) => (res.ok ? (res.json() as Promise<Health>) : Promise.reject(res)))
      .then((body) => setState(body.status === "ok" ? "ok" : "down"))
      .catch(() => setState("down"));
  }, []);

  const label = { checking: "Checking API…", ok: "API connected", down: "API unreachable" }[state];
  const dot = { checking: "bg-zinc-400", ok: "bg-emerald-500", down: "bg-red-500" }[state];

  return (
    <p className="flex items-center gap-2 text-sm text-zinc-600 dark:text-zinc-400">
      <span className={`h-2 w-2 rounded-full ${dot}`} aria-hidden />
      {label}
    </p>
  );
}
