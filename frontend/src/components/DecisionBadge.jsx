const styles = {
  approved: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200",
  denied: "bg-red-50 text-red-700 ring-1 ring-red-200",
  escalated: "bg-amber-50 text-amber-800 ring-1 ring-amber-200"
};

const labels = {
  approved: "Approved",
  denied: "Denied",
  escalated: "Escalated to Senior Agent"
};

export default function DecisionBadge({ decision }) {
  if (!decision) return null;
  return (
    <span className={`inline-flex min-h-7 items-center rounded-full px-3 py-1 text-xs font-semibold ${styles[decision] || "bg-slate-100 text-slate-700 ring-1 ring-slate-200"}`}>
      {labels[decision] || decision}
    </span>
  );
}
