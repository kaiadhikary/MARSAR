// STR PDF downloads & audit logs
export default function ReportsPage() {
  return (
    <main className="p-6">
      <h1 className="mb-4 text-xl font-semibold">Reports</h1>
      <p className="max-w-xl text-sm text-slate-400">
        STR (Suspicious Transaction Report) export isn&apos;t wired up yet —
        the backend&apos;s{" "}
        <code className="rounded bg-slate-800 px-1">
          POST /api/v1/compliance/export-str/&#123;cluster_id&#125;
        </code>{" "}
        route is still a placeholder. Once{" "}
        <code className="rounded bg-slate-800 px-1">app/reports/generator.py</code>{" "}
        is connected to it, PDF downloads will appear here per cluster.
      </p>
    </main>
  );
}
