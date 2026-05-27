import { Link } from "react-router-dom";
import { useState } from "react";
import ChatWindow from "../components/ChatWindow.jsx";

export default function CustomerView() {
  const [customerId, setCustomerId] = useState("C001");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  async function sendMessage(event) {
    event.preventDefault();
    if (!customerId.trim() || !input.trim() || loading) return;
    const trimmedInput = input.trim();
    const normalizedMessageId = /^c[o0]{2}\d$/i.test(trimmedInput) ? `C00${trimmedInput.slice(-1)}` : null;
    const effectiveCustomerId = normalizedMessageId || customerId.trim();
    if (normalizedMessageId) setCustomerId(normalizedMessageId);
    const userMessage = { id: crypto.randomUUID(), role: "user", text: input };
    const history = messages.map(({ role, text, decision }) => ({ role, text, decision: decision || null }));
    setMessages((current) => [...current, userMessage]);
    setInput("");
    setLoading(true);
    try {
      const response = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ customer_id: effectiveCustomerId, message: trimmedInput, history })
      });
      const data = await response.json();
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "agent",
          text: data.reason || "No response returned.",
          decision: data.decision === "none" ? null : data.decision
        }
      ]);
    } catch (error) {
      setMessages((current) => [
        ...current,
        { id: crypto.randomUUID(), role: "agent", text: "The refund service is unavailable. Try again shortly.", decision: "escalated" }
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-line bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-5 py-4">
          <div>
            <h1 className="text-lg font-semibold text-ink">Worknoon Refund Agent</h1>
            <p className="text-sm text-slate-500">Policy-enforced customer refund decisions</p>
          </div>
          <Link to="/admin" className="rounded-md border border-line px-3 py-2 text-sm font-medium text-ink hover:bg-surface">
            Admin
          </Link>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-5 py-6">
        <label className="mb-4 block">
          <span className="mb-1 block text-sm font-medium text-ink">Customer ID</span>
          <input
            value={customerId}
            onChange={(event) => setCustomerId(event.target.value)}
            placeholder="C001"
            className="h-11 w-full rounded-md border border-line bg-white px-3 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          />
        </label>
        <ChatWindow messages={messages} input={input} setInput={setInput} onSend={sendMessage} loading={loading} />
      </main>
    </div>
  );
}
