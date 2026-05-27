import DecisionBadge from "./DecisionBadge.jsx";

function MayaAvatar({ className = "" }) {
  return (
    <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-600 text-sm font-semibold text-white shadow-sm ${className}`}>
      M
    </div>
  );
}

export default function MessageBubble({ message }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex items-end gap-2 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && <MayaAvatar />}
      <div className={`max-w-[82%] ${isUser ? "items-end" : "items-start"}`}>
        <div className={`rounded-2xl px-4 py-3 text-sm leading-6 ${isUser ? "bg-blue-600 text-white" : "bg-white text-slate-800 shadow-sm ring-1 ring-slate-200"}`}>
          <p className="whitespace-pre-wrap">{message.text}</p>
        </div>
        {!isUser && message.decision && (
          <div className="mt-2">
            <DecisionBadge decision={message.decision} />
          </div>
        )}
      </div>
    </div>
  );
}
