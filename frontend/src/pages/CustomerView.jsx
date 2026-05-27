import { Link } from "react-router-dom";
import { useState } from "react";
import ChatWindow from "../components/ChatWindow.jsx";

const CUSTOMERS = [
  { id: "C001", name: "Ava Eligible" },
  { id: "C002", name: "Ben Finalsale" },
  { id: "C003", name: "Cara Late" },
  { id: "C004", name: "Dev Escalate" },
  { id: "C005", name: "Eli Digital" },
  { id: "C006", name: "Faye Defective" },
  { id: "C007", name: "Gia Shipped" },
  { id: "C008", name: "Hari Premium" },
  { id: "C009", name: "Ira Pending" },
  { id: "C010", name: "Jules Processing" },
  { id: "C011", name: "Kai Delivered" },
  { id: "C012", name: "Lena Cancelled" },
  { id: "C013", name: "Mina Delivered" },
  { id: "C014", name: "Noah Premium" },
  { id: "C015", name: "Omar Late" },
];

export default function CustomerView() {
  const [customerId, setCustomerId] = useState("C001");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  function handleCustomerChange(event) {
    setCustomerId(event.target.value);
    setMessages([]);
    setInput("");
  }

  async function sendMessage(event) {
    event.preventDefault();
    if (!customerId.trim() || !input.trim() || loading) return;
    const trimmedInput = input.trim();
    const userMessage = { id: crypto.randomUUID(), role: "user", text: input };
    const history = messages.map(({ role, text, decision }) => ({ role, text, decision: decision || null }));
    setMessages((current) => [...current, userMessage]);
    setInput("");
    setLoading(true);
    try {
      const response = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ customer_id: customerId, message: trimmedInput, history }),
      });
      const data = await response.json();
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "agent",
          text: data.reason || "No response returned.",
          decision: data.decision === "none" ? null : data.decision,
        },
      ]);
    } catch {
      setMessages((current) => [
        ...current,
        { id: crypto.randomUUID(), role: "agent", text: "The refund service is unavailable. Try again shortly.", decision: "escalated" },
      ]);
    } finally {
      setLoading(false);
    }
  }

  const selectedCustomer = CUSTOMERS.find((c) => c.id === customerId);

  return (
    <div className="min-h-screen">
      <header className="border-b border-line bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-5 py-4">
          <div>
            <h1 className="text-lg font-semibold text-ink">Worknoon Refund Agent</h1>
            <p className="text-sm text-slate-500">Policy-enforced customer refund decisions</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-slate-500">Customer</span>
              <select
                value={customerId}
                onChange={handleCustomerChange}
                className="h-9 min-w-[180px] rounded-md border border-line bg-white px-2 text-sm font-medium text-ink outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              >
                {CUSTOMERS.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.id} — {c.name}
                  </option>
                ))}
              </select>
            </div>
            <Link to="/admin" className="rounded-md border border-line px-3 py-2 text-sm font-medium text-ink hover:bg-surface">
              Admin
            </Link>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-5 py-6">
        <ChatWindow messages={messages} input={input} setInput={setInput} onSend={sendMessage} loading={loading} />
      </main>
    </div>
  );
}
