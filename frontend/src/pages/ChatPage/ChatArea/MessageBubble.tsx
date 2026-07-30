import type { MessageItem } from "../../../types";

interface MessageBubbleProps {
  message: MessageItem;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={`flex ${isUser ? "justify-end" : "justify-start"} animate-message-in`}
    >
      <div
        className={`max-w-[80%] px-5 py-3 rounded-bubble text-[15px] leading-6 shadow-sm ${
          isUser
            ? "bg-userbubble text-gray-800 rounded-tr-sm"
            : "bg-gradient-to-br from-coral to-warmorange text-white rounded-tl-sm"
        }`}
      >
        {message.content}
      </div>
    </div>
  );
}
