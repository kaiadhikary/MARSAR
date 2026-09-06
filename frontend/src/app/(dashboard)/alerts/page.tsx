// Real-time mempool radar table
export default function AlertsPage() {
  return (
    <main className="p-6">
      <h1 className="mb-4 text-xl font-semibold">Alerts</h1>
      <p className="max-w-xl text-sm text-slate-400">
        Live alert streaming isn&apos;t wired up yet — the backend&apos;s{" "}
        <code className="rounded bg-slate-800 px-1">/api/v1/alerts/ws</code>{" "}
        WebSocket route is still a placeholder that just echoes a heartbeat.
        Once the scoring engine publishes real high-risk events, this page is
        where they&apos;ll show up as a live table.
      </p>
    </main>
  );
}
