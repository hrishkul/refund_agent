const styles = {
  approved: "bg-emerald-100 text-emerald-800 border-emerald-200",
  denied: "bg-red-100 text-red-800 border-red-200",
  escalated: "bg-amber-100 text-amber-800 border-amber-200"
};

export default function DecisionBadge({ decision }) {
  if (!decision) return null;
  return (
    <span className={`inline-flex h-7 items-center rounded-full border px-3 text-xs font-semibold uppercase tracking-normal ${styles[decision] || "bg-slate-100 text-slate-700 border-slate-200"}`}>
      {decision}
    </span>
  );
}
