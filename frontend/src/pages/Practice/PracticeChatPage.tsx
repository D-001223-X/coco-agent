import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { MainLayout } from "../../components/Layout/MainLayout";
import { ChatBubble } from "../../components/Practice/ChatBubble";
import { ChatInput } from "../../components/Practice/ChatInput";
import { ScenarioSelector } from "../../components/Practice/ScenarioSelector";
import { usePracticeStore } from "../../store/practiceStore";

export default function PracticeChatPage() {
  const navigate = useNavigate();
  const {
    sessionId,
    currentModeId,
    currentScenario,
    modes,
    chatMessages,
    chatting,
    sendChat,
    switchScenario,
    endSession,
    error,
  } = usePracticeStore();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [showSelector, setShowSelector] = useState(false);

  useEffect(() => {
    if (!sessionId) {
      navigate("/practice/modes", { replace: true });
    }
  }, [sessionId, navigate]);

  // 自动滚动到底部
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [chatMessages.length]);

  const currentMode = modes.find((m) => m.id === currentModeId) ?? null;
  const currentScenarioName = currentMode?.scenarios.find(
    (s) => s.id === currentScenario
  )?.name;

  const handleSend = async (message: string) => {
    await sendChat(message);
  };

  const handleSwitch = async (scenarioId: string) => {
    await switchScenario(scenarioId);
    setShowSelector(false);
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
        {/* 顶部工具栏：返回 + 模式 + 场景 + 切换 */}
        <div className="h-14 px-6 bg-white border-b border-gray-100 flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-2 min-w-0">
            <button
              onClick={() => navigate("/practice/modes")}
              className="text-gray-500 hover:text-coral transition-colors shrink-0"
              title="返回模式选择"
            >
              ← 返回
            </button>
            <span className="font-semibold text-gray-800 truncate">
              {currentMode?.icon} {currentMode?.label}
            </span>
            <span className="text-gray-300">·</span>
            <span className="text-sm text-gray-500 truncate">
              {currentScenarioName ?? currentScenario}
            </span>
            <button
              onClick={() => setShowSelector((v) => !v)}
              className="text-sm text-coral hover:underline shrink-0"
            >
              {showSelector ? "收起" : "切换"}
            </button>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-400 hidden sm:block">
              {chatMessages.filter((m) => m.role === "user").length} 轮对话
            </span>
            <button
              onClick={handleEnd}
              className="px-4 py-1.5 rounded-button text-xs font-semibold text-gray-500 border border-gray-200 hover:text-coral hover:border-coral/40 transition-colors"
            >
              结束会话
            </button>
          </div>
        </div>

        {/* 场景切换面板 */}
        {showSelector && currentMode && (
          <div className="bg-warmwhite border-b border-gray-100 p-4 max-h-56 overflow-y-auto custom-scrollbar">
            <ScenarioSelector
              scenarios={currentMode.scenarios}
              selectedId={currentScenario ?? ""}
              onSelect={handleSwitch}
            />
          </div>
        )}

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
