// Overview telemetry and high-risk metrics
import Link from "next/link";

export default function DashboardOverviewPage() {
  return (
    <main className="p-6">
      <h1 className="mb-4 text-xl font-semibold">Overview</h1>
      <p className="mb-6 max-w-xl text-sm text-slate-400">
        This dashboard talks to the MARSAR FastAPI backend running on{" "}
        <code className="rounded bg-slate-800 px-1">localhost:8000</code>. Start
        with the Investigator tab to search an address and see its cluster
        graph.
      </p>
      <Link
        href="/investigator"
        className="inline-block rounded-md bg-blue-600 px-4 py-2 text-sm font-medium hover:bg-blue-500"
      >
        Open Investigator →
      </Link>
    </main>
  );
}
