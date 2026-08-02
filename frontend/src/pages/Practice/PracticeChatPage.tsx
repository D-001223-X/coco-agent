import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { MainLayout } from "../../components/Layout/MainLayout";
import { ChatBubble } from "../../components/Practice/ChatBubble";
import { ChatInput } from "../../components/Practice/ChatInput";
import { usePracticeStore } from "../../store/practiceStore";

export default function PracticeChatPage() {
  const navigate = useNavigate();
  const { sessionId, chatMessages, chatting, sendChat, endSession, error } =
    usePracticeStore();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!sessionId) {
      navigate("/practice/modes", { replace: true });
    }
  }, [sessionId, navigate]);

  // 自动滚动到底部
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [chatMessages.length]);

  const handleSend = async (message: string) => {
    await sendChat(message);
  };

  const handleEnd = async () => {
    if (window.confirm("确定结束本次陪练吗？")) {
      await endSession();
      navigate("/practice/modes");
    }
  };

  return (
    <MainLayout>
      <div className="flex-1 flex flex-col h-[calc(100vh-64px)]">
        {/* 头部 */}
        <div className="h-14 px-6 bg-white border-b border-gray-100 flex items-center justify-between shadow-sm">
          <h2 className="text-base font-semibold text-gray-800">口语陪练</h2>
          <button
            onClick={handleEnd}
            className="px-4 py-1.5 rounded-button text-xs font-semibold text-gray-500 border border-gray-200 hover:text-coral hover:border-coral/40 transition-colors"
          >
            结束会话
          </button>
        </div>

        {/* 消息列表 */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-4 bg-warmwhite custom-scrollbar">
          {chatMessages.map((msg) => (
            <ChatBubble key={msg.id} message={msg} />
          ))}
          {chatting && (
            <div className="flex justify-start">
              <div className="bg-white border border-gray-100 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
                <span className="text-sm text-gray-400">Agent 思考中...</span>
              </div>
            </div>
          )}
        </div>

        {/* 输入区 */}
        <div className="p-4 bg-white border-t border-gray-100">
          <ChatInput disabled={chatting} onSend={handleSend} />
          {error && <p className="text-xs text-coral mt-2">{error}</p>}
        </div>
      </div>
    </MainLayout>
  );
}
