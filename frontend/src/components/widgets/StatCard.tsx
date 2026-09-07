interface StatCardProps {
  label: string;
  value: string | number;
  sub?: string;
  accent?: "blue" | "amber" | "red" | "emerald" | "violet";
}

const accentMap = {
  blue: "border-blue-500/40 bg-blue-500/5",
  amber: "border-amber-500/40 bg-amber-500/5",
  red: "border-red-500/40 bg-red-500/5",
  emerald: "border-emerald-500/40 bg-emerald-500/5",
  violet: "border-violet-500/40 bg-violet-500/5",
};

export default function StatCard({
  label,
  value,
  sub,
  accent = "blue",
}: StatCardProps) {
  return (
    <div
      className={`rounded-lg border p-4 ${accentMap[accent]}`}
    >
      <p className="text-xs font-medium uppercase tracking-wider text-slate-400">
        {label}
      </p>
      <p className="mt-1 text-2xl font-bold text-slate-100">{value}</p>
      {sub && <p className="mt-1 text-xs text-slate-500">{sub}</p>}
    </div>
  );
}
