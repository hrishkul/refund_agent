export default function ReasoningLog({ trace }) {
  if (!trace) return null;
  return (
    <div className="rounded-lg border border-line bg-white p-4 text-sm text-slate-600">
      <p className="font-semibold text-ink">Policy Rule</p>
      <p className="mt-1">{trace.policy_rule || "none"}</p>
    </div>
  );
}
