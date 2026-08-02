import { useState } from "react";

interface ChatInputProps {
  disabled: boolean;
  onSend: (message: string) => void;
}

export function ChatInput({ disabled, onSend }: ChatInputProps) {
  const [text, setText] = useState("");

  const handleSend = () => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
  };

  return (
    <div className="flex gap-2">
      <input
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
          }
        }}
        placeholder="输入英文消息...（Enter 发送）"
        disabled={disabled}
        className="flex-1 px-4 py-3 border border-gray-200 rounded-button text-sm focus:outline-none focus:ring-2 focus:ring-coral/30 disabled:opacity-50"
      />
      <button
        onClick={handleSend}
        disabled={disabled || !text.trim()}
        className="px-6 py-3 rounded-button bg-coral hover:bg-coral-hover text-white text-sm font-semibold disabled:opacity-40 transition-colors"
      >
        发送
      </button>
    </div>
  );
}
