import { Send, Loader2 } from "lucide-react";
import MessageBubble from "./MessageBubble.jsx";

export default function ChatWindow({ messages, input, setInput, onSend, loading }) {
  return (
    <section className="flex min-h-[620px] flex-col overflow-hidden rounded-lg border border-line bg-surface">
      <div className="flex-1 space-y-4 overflow-y-auto p-5">
        {messages.length === 0 ? (
          <div className="flex h-full min-h-[420px] items-center justify-center text-center text-sm text-slate-500">
            Enter your customer ID and describe your refund request
          </div>
        ) : (
          messages.map((message) => <MessageBubble key={message.id} message={message} />)
        )}
      </div>
      <form onSubmit={onSend} className="flex gap-3 border-t border-line bg-white p-4">
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
          placeholder="Describe the refund request..."
          className="h-12 flex-1 rounded-md border border-line px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
        />
        <button
          type="submit"
          disabled={loading}
          className="inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-md bg-blue-600 text-white disabled:cursor-not-allowed disabled:bg-slate-300"
          aria-label="Send message"
        >
          {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
        </button>
      </form>
    </section>
  );
}
