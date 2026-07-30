import { useState } from "react";

interface MessageInputProps {
  onSend: (content: string) => void;
  disabled?: boolean;
}

export function MessageInput({ onSend, disabled }: MessageInputProps) {
  const [content, setContent] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim() || disabled) return;
    onSend(content.trim());
    setContent("");
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="p-4 bg-white border-t border-gray-100 flex items-end gap-3"
    >
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSubmit(e);
          }
        }}
        placeholder="输入消息，按 Enter 发送..."
        disabled={disabled}
        rows={1}
        className="flex-1 min-h-[48px] max-h-32 px-4 py-3 rounded-input border border-gray-200 bg-white text-gray-800 placeholder-gray-400 outline-none focus:ring-2 focus:ring-coral/30 focus:border-coral resize-none transition-all disabled:opacity-60"
      />
      <button
        type="submit"
        disabled={disabled || !content.trim()}
        className="px-6 py-3 rounded-button bg-coral hover:bg-coral-hover disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold transition-all shadow-md hover:shadow-lg"
      >
        发送
      </button>
    </form>
  );
}
