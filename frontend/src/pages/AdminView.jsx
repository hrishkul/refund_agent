import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import AdminDashboard from "../components/AdminDashboard.jsx";

export default function AdminView() {
  const [traces, setTraces] = useState([]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const response = await fetch("/api/traces");
        const data = await response.json();
        if (!cancelled) setTraces(data);
      } catch {
        if (!cancelled) setTraces([]);
      }
    }
    load();
    const timer = setInterval(load, 5000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  return (
    <div className="min-h-screen">
      <header className="border-b border-line bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4">
          <div>
            <h1 className="text-lg font-semibold text-ink">Refund Operations</h1>
            <p className="text-sm text-slate-500">Agent traces, policy outcomes, and token costs</p>
          </div>
          <Link to="/" className="rounded-md border border-line px-3 py-2 text-sm font-medium text-ink hover:bg-surface">
            Customer
          </Link>
        </div>
      </header>
      <AdminDashboard traces={traces} />
    </div>
  );
}
