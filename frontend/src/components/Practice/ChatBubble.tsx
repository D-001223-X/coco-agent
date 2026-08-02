import type { ChatMessage } from "../../store/practiceStore";
import { CorrectionDisplay } from "./CorrectionDisplay";
import { AgentThoughtDisplay } from "./AgentThoughtDisplay";

interface ChatBubbleProps {
  message: ChatMessage;
}

export function ChatBubble({ message }: ChatBubbleProps) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 shadow-sm ${
          isUser
            ? "bg-coral text-white rounded-br-sm"
            : "bg-white border border-gray-100 rounded-bl-sm"
        }`}
      >
        <p className={`text-sm whitespace-pre-wrap ${isUser ? "" : "text-gray-800"}`}>
          {message.content}
        </p>

        {!isUser && message.correction && (
          <div className="mt-2">
            <CorrectionDisplay correction={message.correction} />
          </div>
        )}
        {!isUser && message.agentThought && (
          <div className="mt-2">
            <AgentThoughtDisplay thought={message.agentThought} />
          </div>
        )}
      </div>
    </div>
  );
}
