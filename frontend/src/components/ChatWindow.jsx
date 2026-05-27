import { ArrowUp, Loader2 } from "lucide-react";
import MessageBubble from "./MessageBubble.jsx";

function MayaAvatar() {
  return (
    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-blue-600 text-sm font-semibold text-white shadow-sm">
      M
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-2 text-sm text-slate-500">
      <MayaAvatar />
      <div className="rounded-2xl bg-white px-4 py-3 shadow-sm ring-1 ring-slate-200">
        <span>Maya is reviewing your order</span>
        <span className="ml-1 inline-flex w-8 justify-between align-middle">
          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.2s]" />
          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.1s]" />
          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400" />
        </span>
      </div>
    </div>
  );
}

export default function ChatWindow({ messages, input, setInput, onSend, loading }) {
  return (
    <section className="flex h-full min-h-[640px] flex-col bg-slate-50 lg:min-h-0">
      <header className="flex h-20 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-5">
        <div className="flex items-center gap-3">
          <MayaAvatar />
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold text-slate-950">Maya</h2>
              <span className="h-2 w-2 rounded-full bg-emerald-500" />
            </div>
            <p className="text-xs text-slate-500">ShopEase Support</p>
          </div>
        </div>
      </header>

      <div className="flex-1 space-y-4 overflow-y-auto p-5">
        {messages.length === 0 ? (
          <div className="flex h-full min-h-[360px] items-center justify-center text-center text-sm text-slate-500">
            Ask Maya about an order, return, refund, or ShopEase policy.
          </div>
        ) : (
          messages.map((message) => <MessageBubble key={message.id} message={message} />)
        )}
        {loading && <TypingIndicator />}
      </div>

      <form onSubmit={onSend} className="flex shrink-0 gap-3 border-t border-slate-200 bg-white p-4">
        <input
          type="text"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && input.trim() && !loading) {
              event.preventDefault();
              event.currentTarget.form?.requestSubmit();
            }
          }}
          placeholder="Message Maya..."
          className="h-11 min-w-0 flex-1 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
        />
        <button
          type="submit"
          disabled={loading}
          className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-blue-600 text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
          aria-label="Send message"
        >
          {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <ArrowUp className="h-5 w-5" />}
        </button>
      </form>
    </section>
  );
}
