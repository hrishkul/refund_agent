import { useState } from "react";
import DecisionBadge from "./DecisionBadge.jsx";
import StatCard from "./StatCard.jsx";

const TOOL_CALL_STEPS = {
  approved: [
    { tool: "get_customer_order", label: "Fetched customer order", icon: "🔍" },
    { tool: "check_refund_policy", label: "Ran policy engine", icon: "⚖️" },
    { tool: "decision", label: "Decision produced", icon: "✅" },
  ],
  denied: [
    { tool: "get_customer_order", label: "Fetched customer order", icon: "🔍" },
    { tool: "check_refund_policy", label: "Ran policy engine", icon: "⚖️" },
    { tool: "decision", label: "Decision produced", icon: "🚫" },
  ],
  escalated: [
    { tool: "get_customer_order", label: "Fetched customer order", icon: "🔍" },
    { tool: "check_refund_policy", label: "Ran policy engine — threshold exceeded", icon: "⚖️" },
    { tool: "decision", label: "Escalated to human agent", icon: "🔺" },
  ],
  none: [
    { tool: "response", label: "Conversational response — no tool calls", icon: "💬" },
  ],
};

function TraceExpand({ trace }) {
  const steps = TOOL_CALL_STEPS[trace.decision] || TOOL_CALL_STEPS.none;
  return (
    <div className="border-t border-line bg-slate-50 px-4 py-4">
      <div className="grid gap-4 lg:grid-cols-2">
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Agent Tool Call Trace</p>
          <ol className="space-y-2">
            {steps.map((step, i) => (
              <li key={i} className="flex items-start gap-2 text-sm">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-white text-xs shadow-sm ring-1 ring-line">
                  {i + 1}
                </span>
                <div>
                  <span className="mr-1.5">{step.icon}</span>
                  <span className="font-medium text-ink">{step.label}</span>
                  <code className="ml-2 rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-500">{step.tool}()</code>
                </div>
              </li>
            ))}
          </ol>
        </div>

        <div className="space-y-3">
          <div>
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">Full Agent Response</p>
            <p className="rounded-md border border-line bg-white p-3 text-sm leading-relaxed text-slate-700">{trace.agent_response}</p>
          </div>
          {trace.policy_rule && (
            <div>
              <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">Policy Rule Triggered</p>
              <code className="rounded bg-amber-50 px-2 py-1 text-xs font-medium text-amber-700 ring-1 ring-amber-200">{trace.policy_rule}</code>
            </div>
          )}
          <div className="flex flex-wrap gap-4 text-xs text-slate-500">
            <span>🪙 <strong className="text-ink">{(trace.prompt_tokens + trace.completion_tokens).toLocaleString()}</strong> tokens ({trace.prompt_tokens} in / {trace.completion_tokens} out)</span>
            <span>💰 <strong className="text-ink">${trace.cost_usd.toFixed(6)}</strong></span>
            <span>⏱ <strong className="text-ink">{trace.latency_ms} ms</strong></span>
            <span>🤖 <strong className="text-ink">{trace.model_used || "n/a"}</strong></span>
          </div>
        </div>
      </div>
    </div>
  );
}

function TraceRow({ trace }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <>
      <tr
        className="cursor-pointer transition hover:bg-slate-50"
        onClick={() => setExpanded((v) => !v)}
      >
        <td className="px-4 py-3 text-slate-500">
          <span className="mr-1.5 text-slate-400">{expanded ? "▾" : "▸"}</span>
          {new Date(trace.timestamp).toLocaleTimeString()}
        </td>
        <td className="px-4 py-3">
          <div className="font-medium text-ink">{trace.customer_name}</div>
          <div className="text-xs text-slate-400">{trace.customer_id ? trace.customer_id.slice(0, 8) : "unknown"}</div>
        </td>
        <td className="max-w-[220px] px-4 py-3 text-slate-600">
          <p className="line-clamp-2">{trace.user_message}</p>
        </td>
        <td className="max-w-[260px] px-4 py-3 text-slate-600">
          <p className="line-clamp-2">{trace.agent_response}</p>
        </td>
        <td className="px-4 py-3"><DecisionBadge decision={trace.decision} /></td>
        <td className="px-4 py-3 text-slate-600">{trace.model_used || "n/a"}</td>
        <td className="px-4 py-3 text-slate-600">{(trace.prompt_tokens + trace.completion_tokens).toLocaleString()}</td>
        <td className="px-4 py-3 text-slate-600">${trace.cost_usd.toFixed(6)}</td>
        <td className="px-4 py-3 text-slate-600">{trace.latency_ms} ms</td>
        <td className="px-4 py-3 text-slate-600">{trace.status}</td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={10} className="p-0">
            <TraceExpand trace={trace} />
          </td>
        </tr>
      )}
    </>
  );
}

export default function AdminDashboard({ traces }) {
  const totalTokens = traces.reduce((sum, t) => sum + t.prompt_tokens + t.completion_tokens, 0);
  const totalCost = traces.reduce((sum, t) => sum + t.cost_usd, 0);
  const avgLatency = traces.length ? Math.round(traces.reduce((sum, t) => sum + t.latency_ms, 0) / traces.length) : 0;

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
          <p className="text-xs text-slate-400">Click any row to expand the agent reasoning trace</p>
        </div>
        {traces.length === 0 ? (
          <div className="p-10 text-center text-sm text-slate-500">No traces yet — send a message in the customer view to generate one</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1180px] text-left text-sm">
              <thead className="bg-surface text-xs uppercase tracking-normal text-slate-500">
                <tr>
                  <th className="px-4 py-3">Time</th>
                  <th className="px-4 py-3">Customer</th>
                  <th className="px-4 py-3">Customer Message</th>
                  <th className="px-4 py-3">Maya Response</th>
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
                  <TraceRow key={trace.id} trace={trace} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
