import { ApiStatus } from "@/components/api-status";

export default function Home() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-4 px-4 text-center">
      <h1 className="text-4xl font-semibold tracking-tight">Veylith</h1>
      <p className="max-w-md text-zinc-600 dark:text-zinc-400">
        Continuous security scanning for your GitHub repositories.
      </p>
      <ApiStatus />
    </main>
  );
}
