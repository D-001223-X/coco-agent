import { useEffect, useState } from "react";

interface MessageInputProps {
  onSend: (content: string) => void;
  disabled?: boolean;
}

export function MessageInput({ onSend, disabled }: MessageInputProps) {
  const [content, setContent] = useState("");

  // T-005 移动端键盘防遮挡：键盘弹出时输入框滚动到可视区
  useEffect(() => {
    const handleViewportChange = () => {
      const input = document.getElementById("chat-input");
      if (input && window.visualViewport) {
        const viewport = window.visualViewport;
        const keyboardHeight = window.innerHeight - viewport.height;
        if (keyboardHeight > 100) {
          input.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      }
    };
    window.visualViewport?.addEventListener("resize", handleViewportChange);
    return () =>
      window.visualViewport?.removeEventListener("resize", handleViewportChange);
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim() || disabled) return;
    onSend(content.trim());
    setContent("");
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="p-3 md:p-4 bg-white border-t border-gray-100 flex items-end gap-2 md:gap-3"
    >
      <textarea
        id="chat-input"
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
        className="px-5 md:px-6 min-h-[48px] rounded-button bg-coral hover:bg-coral-hover disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold transition-all shadow-md hover:shadow-lg"
      >
        发送
      </button>
    </form>
  );
}
