import DecisionBadge from "./DecisionBadge.jsx";

export default function MessageBubble({ message }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[82%] rounded-lg border px-4 py-3 shadow-sm ${isUser ? "border-blue-200 bg-blue-600 text-white" : "border-line bg-white text-ink"}`}>
        <div className="mb-2 flex items-center gap-2">
          <span className={`text-xs font-semibold ${isUser ? "text-blue-50" : "text-slate-500"}`}>
            {isUser ? "You" : "Refund Agent"}
          </span>
          {!isUser && <DecisionBadge decision={message.decision} />}
        </div>
        <p className="whitespace-pre-wrap text-sm leading-6">{message.text}</p>
      </div>
    </div>
  );
}
