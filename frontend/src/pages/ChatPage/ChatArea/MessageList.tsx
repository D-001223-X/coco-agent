import { useEffect, useRef } from "react";
import { MessageBubble } from "./MessageBubble";
import type { MessageItem } from "../../../types";

interface MessageListProps {
  messages: MessageItem[];
  isLoading: boolean;
}

export function MessageList({ messages, isLoading }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  return (
    <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-4">
      {messages.length === 0 && !isLoading && (
        <div className="h-full flex flex-col items-center justify-center text-gray-400">
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-coral to-warmorange flex items-center justify-center text-white text-2xl mb-4">
            🤖
          </div>
          <p className="text-base">开始一段新对话吧</p>
        </div>
      )}

      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}

      {isLoading && (
        <div className="flex justify-start animate-message-in">
          <div className="bg-gradient-to-br from-coral to-warmorange text-white px-5 py-3 rounded-bubble rounded-tl-sm shadow-sm">
            <div className="flex gap-1.5">
              <span
                className="w-2 h-2 bg-white/80 rounded-full animate-bounce"
                style={{ animationDelay: "0ms" }}
              />
              <span
                className="w-2 h-2 bg-white/80 rounded-full animate-bounce"
                style={{ animationDelay: "150ms" }}
              />
              <span
                className="w-2 h-2 bg-white/80 rounded-full animate-bounce"
                style={{ animationDelay: "300ms" }}
              />
            </div>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
