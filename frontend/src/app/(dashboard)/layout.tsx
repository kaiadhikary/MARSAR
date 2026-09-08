import Link from "next/link";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      <nav className="w-48 shrink-0 border-r border-slate-800 p-4">
        <p className="mb-6 text-sm font-semibold tracking-wide text-slate-400">MARSAR</p>
        <ul className="space-y-2 text-sm">
          <li><Link href="/" className="hover:text-blue-400">Overview</Link></li>
          <li><Link href="/investigator" className="hover:text-blue-400">Investigator</Link></li>
          <li><Link href="/alerts" className="hover:text-blue-400">Alerts</Link></li>
          <li><Link href="/reports" className="hover:text-blue-400">Reports</Link></li>
        </ul>
      </nav>
      <div className="flex-1">{children}</div>
    </div>
  );
}
