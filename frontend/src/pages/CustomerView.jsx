import { Link } from "react-router-dom";
import { useMemo, useState } from "react";
import { ArrowUpRight, ChevronDown, PackageCheck, RefreshCcw } from "lucide-react";
import ChatWindow from "../components/ChatWindow.jsx";

const customers = {
  C001: "Ava Eligible",
  C002: "Ben Finalsale",
  C003: "Cara Late",
  C004: "Dev Escalate",
  C005: "Eli Digital",
  C006: "Faye Defective",
  C007: "Gia Shipped",
  C008: "Hari Premium"
};

const orders = [
  {
    id: "C001",
    customer: "Ava Eligible",
    product: "Everyday Hoodie",
    date: "May 17, 2026",
    status: "delivered",
    total: "$89.00",
    image: "https://images.unsplash.com/photo-1556821840-3a63f95609a7?auto=format&fit=crop&w=240&q=80"
  },
  {
    id: "C002",
    customer: "Ben Finalsale",
    product: "Final Sale Sneakers",
    date: "May 19, 2026",
    status: "delivered",
    total: "$120.00",
    image: "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=240&q=80"
  },
  {
    id: "C004",
    customer: "Dev Escalate",
    product: "OLED Monitor",
    date: "May 15, 2026",
    status: "delivered",
    total: "$750.00",
    image: "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?auto=format&fit=crop&w=240&q=80"
  },
  {
    id: "C005",
    customer: "Eli Digital",
    product: "Design Template Pack",
    date: "May 24, 2026",
    status: "delivered",
    total: "$49.00",
    image: "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=240&q=80"
  },
  {
    id: "C006",
    customer: "Faye Defective",
    product: "Smart Kettle",
    date: "Apr 7, 2026",
    status: "delivered",
    total: "$99.00",
    image: "https://images.unsplash.com/photo-1608354580875-30bd4168b351?auto=format&fit=crop&w=240&q=80"
  },
  {
    id: "C007",
    customer: "Gia Shipped",
    product: "Everyday Hoodie",
    date: "May 25, 2026",
    status: "shipped",
    total: "$89.00",
    image: "https://images.unsplash.com/photo-1578681994506-b8f463449011?auto=format&fit=crop&w=240&q=80"
  },
  {
    id: "C008",
    customer: "Hari Premium",
    product: "Noise Cancelling Headphones",
    date: "Apr 17, 2026",
    status: "delivered",
    total: "$240.00",
    image: "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=240&q=80"
  },
  {
    id: "C010",
    customer: "Jules Processing",
    product: "Noise Cancelling Headphones",
    date: "May 23, 2026",
    status: "processing",
    total: "$240.00",
    image: "https://images.unsplash.com/photo-1484704849700-f032a568e944?auto=format&fit=crop&w=240&q=80"
  }
];

const statusStyles = {
  delivered: {
    badge: "bg-emerald-50 text-emerald-700 ring-emerald-200",
    rail: "bg-emerald-500"
  },
  shipped: {
    badge: "bg-amber-50 text-amber-800 ring-amber-200",
    rail: "bg-amber-500"
  },
  processing: {
    badge: "bg-slate-100 text-slate-600 ring-slate-200",
    rail: "bg-slate-400"
  }
};

function ShopEaseLogo() {
  return (
    <div className="flex items-center gap-3">
      <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600 text-white shadow-sm">
        <PackageCheck className="h-5 w-5" />
      </div>
      <div>
        <p className="text-sm font-semibold text-slate-950">ShopEase</p>
        <p className="text-xs text-slate-500">Customer orders</p>
      </div>
    </div>
  );
}

function StatusBadge({ status }) {
  const styles = statusStyles[status] || statusStyles.processing;
  return (
    <span className={`inline-flex h-6 items-center rounded-full px-2.5 text-xs font-medium capitalize ring-1 ${styles.badge}`}>
      {status}
    </span>
  );
}

function OrderCard({ order, active, onSelect, onRefund }) {
  const styles = statusStyles[order.status] || statusStyles.processing;
  return (
    <article
      className={`group relative overflow-hidden rounded-lg bg-white shadow-sm ring-1 ring-slate-200 transition hover:-translate-y-0.5 hover:shadow-md ${active ? "ring-blue-200" : ""}`}
    >
      <div className={`absolute inset-y-0 left-0 w-1 ${styles.rail}`} />
      <button type="button" onClick={onSelect} className="flex w-full gap-4 p-4 text-left">
        <img src={order.image} alt={order.product} className="h-20 w-20 shrink-0 rounded-md object-cover" loading="lazy" />
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h3 className="truncate text-sm font-semibold text-slate-950">{order.product}</h3>
              <p className="mt-1 text-xs text-slate-500">{order.customer}</p>
            </div>
            <StatusBadge status={order.status} />
          </div>
          <div className="mt-4 flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="text-xs text-slate-500">Order date</p>
              <p className="text-sm font-medium text-slate-700">{order.date}</p>
            </div>
            <div className="text-right">
              <p className="text-xs text-slate-500">Order total</p>
              <p className="text-sm font-semibold text-slate-950">{order.total}</p>
            </div>
          </div>
        </div>
      </button>
      <button
        type="button"
        onClick={onRefund}
        className="absolute bottom-4 right-4 inline-flex h-8 items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 text-xs font-medium text-slate-700 opacity-0 shadow-sm transition hover:border-blue-200 hover:text-blue-700 group-hover:opacity-100"
      >
        <RefreshCcw className="h-3.5 w-3.5" />
        Request Refund
      </button>
    </article>
  );
}

export default function CustomerView() {
  const [customerId, setCustomerId] = useState("C001");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  const selectedCustomer = customers[customerId] || orders.find((order) => order.id === customerId)?.customer || "Guest";
  const visibleOrders = useMemo(() => orders.filter((order) => order.id === customerId), [customerId]);
  const displayedOrders = visibleOrders.length ? visibleOrders : orders.slice(0, 4);

  async function submitMessage(messageText) {
    if (!customerId.trim() || !messageText.trim() || loading) return;
    const trimmedInput = messageText.trim();
    const normalizedMessageId = /^c[o0]{2}\d$/i.test(trimmedInput) ? `C00${trimmedInput.slice(-1)}` : null;
    const effectiveCustomerId = normalizedMessageId || customerId.trim();
    if (normalizedMessageId) setCustomerId(normalizedMessageId);
    const userMessage = { id: crypto.randomUUID(), role: "user", text: trimmedInput };
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
        { id: crypto.randomUUID(), role: "agent", text: "I can't reach the refund service right now. Please make sure the backend is running and try again.", decision: null }
      ]);
    } finally {
      setLoading(false);
    }
  }

  function sendMessage(event) {
    event.preventDefault();
    submitMessage(input);
  }

  function selectOrder(order) {
    setCustomerId(order.id);
    setInput(`show my orders`);
  }

  function requestRefund(order) {
    setCustomerId(order.id);
    submitMessage(`I want to return my ${order.product}`);
  }

  return (
    <div className="min-h-screen bg-[#f5f5f5] text-slate-950 lg:h-screen lg:overflow-hidden">
      <div className="flex min-h-screen flex-col lg:h-screen lg:flex-row">
        <section className="flex min-h-[58vh] flex-col lg:h-screen lg:w-[60%]">
          <header className="flex shrink-0 items-center justify-between border-b border-slate-200 bg-[#f5f5f5] px-5 py-5 sm:px-8">
            <ShopEaseLogo />
            <Link to="/admin" className="inline-flex h-9 items-center gap-1 rounded-full border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 shadow-sm transition hover:border-blue-200 hover:text-blue-700">
              Admin
              <ArrowUpRight className="h-4 w-4" />
            </Link>
          </header>

          <div className="flex shrink-0 flex-col gap-4 px-5 py-5 sm:px-8">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <h1 className="text-2xl font-semibold tracking-normal text-slate-950">My Orders</h1>
                <p className="mt-1 text-sm text-slate-500">Viewing orders for: <span className="font-medium text-slate-700">{selectedCustomer}</span></p>
              </div>
              <label className="relative w-full sm:w-64">
                <span className="mb-1 block text-xs font-medium text-slate-500">Customer ID</span>
                <select
                  value={customerId}
                  onChange={(event) => setCustomerId(event.target.value)}
                  className="h-10 w-full appearance-none rounded-md border border-slate-200 bg-white px-3 pr-9 text-sm font-medium text-slate-800 shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                >
                  {Object.entries(customers).map(([id, name]) => (
                    <option key={id} value={id}>{id} - {name}</option>
                  ))}
                </select>
                <ChevronDown className="pointer-events-none absolute bottom-3 right-3 h-4 w-4 text-slate-400" />
              </label>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto px-5 pb-6 sm:px-8">
            <div className="grid gap-4">
              {displayedOrders.map((order) => (
                <OrderCard
                  key={`${order.id}-${order.product}`}
                  order={order}
                  active={order.id === customerId}
                  onSelect={() => selectOrder(order)}
                  onRefund={() => requestRefund(order)}
                />
              ))}
            </div>
          </div>
        </section>

        <aside className="min-h-[680px] border-t border-slate-200 bg-white shadow-[0_-8px_28px_rgba(15,23,42,0.08)] lg:h-screen lg:min-h-0 lg:w-[40%] lg:border-l lg:border-t-0 lg:shadow-[-12px_0_32px_rgba(15,23,42,0.10)]">
          <ChatWindow messages={messages} input={input} setInput={setInput} onSend={sendMessage} loading={loading} />
        </aside>
      </div>
    </div>
  );
}
