import DecisionBadge from "./DecisionBadge.jsx";
import StatCard from "./StatCard.jsx";

export default function AdminDashboard({ traces }) {
  const totalTokens = traces.reduce((sum, trace) => sum + trace.prompt_tokens + trace.completion_tokens, 0);
  const totalCost = traces.reduce((sum, trace) => sum + trace.cost_usd, 0);
  const avgLatency = traces.length ? Math.round(traces.reduce((sum, trace) => sum + trace.latency_ms, 0) / traces.length) : 0;

  return (
    <main className="mx-auto w-full max-w-7xl px-5 py-6">
      <div className="grid gap-4 md:grid-cols-4">
        <StatCard label="Total Runs" value={traces.length} />
        <StatCard label="Total Tokens" value={totalTokens.toLocaleString()} />
        <StatCard label="Total Cost ($)" value={totalCost.toFixed(6)} />
        <StatCard label="Avg Latency (ms)" value={avgLatency.toLocaleString()} />
      </div>
      <section className="mt-6 overflow-hidden rounded-lg border border-line bg-white shadow-sm">
        <div className="border-b border-line px-4 py-3">
          <h2 className="text-sm font-semibold text-ink">Recent Traces</h2>
        </div>
        {traces.length === 0 ? (
          <div className="p-10 text-center text-sm text-slate-500">No traces yet</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[920px] text-left text-sm">
              <thead className="bg-surface text-xs uppercase tracking-normal text-slate-500">
                <tr>
                  <th className="px-4 py-3">Time</th>
                  <th className="px-4 py-3">Customer</th>
                  <th className="px-4 py-3">Decision</th>
                  <th className="px-4 py-3">Model</th>
                  <th className="px-4 py-3">Tokens</th>
                  <th className="px-4 py-3">Cost</th>
                  <th className="px-4 py-3">Latency</th>
                  <th className="px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {traces.map((trace) => (
                  <tr key={trace.id}>
                    <td className="px-4 py-3 text-slate-600">{new Date(trace.timestamp).toLocaleTimeString()}</td>
                    <td className="px-4 py-3">
                      <div className="font-medium text-ink">{trace.customer_name}</div>
                      <div className="text-xs text-slate-500">{trace.customer_id.slice(0, 8)}</div>
                    </td>
                    <td className="px-4 py-3"><DecisionBadge decision={trace.decision} /></td>
                    <td className="px-4 py-3 text-slate-600">{trace.model_used}</td>
                    <td className="px-4 py-3 text-slate-600">{(trace.prompt_tokens + trace.completion_tokens).toLocaleString()}</td>
                    <td className="px-4 py-3 text-slate-600">${trace.cost_usd.toFixed(6)}</td>
                    <td className="px-4 py-3 text-slate-600">{trace.latency_ms} ms</td>
                    <td className="px-4 py-3 text-slate-600">{trace.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
