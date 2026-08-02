import { useState } from "react";
import type { ChatMessage } from "../../store/practiceStore";
import { CorrectionDisplay } from "./CorrectionDisplay";
import { AgentThoughtDisplay } from "./AgentThoughtDisplay";

interface ChatBubbleProps {
  message: ChatMessage;
}

export function ChatBubble({ message }: ChatBubbleProps) {
  const isUser = message.role === "user";
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const reactLoop = message.reactLoop ?? [];
  const naturalSummary = message.naturalSummary;

  const copyJSON = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(reactLoop, null, 2));
    } catch (err) {
      // 降级方案：document.execCommand
      const textarea = document.createElement("textarea");
      textarea.value = JSON.stringify(reactLoop, null, 2);
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

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

        {/* Agent 完整推理过程 */}
        {!isUser && reactLoop.length > 0 && (
          <div className="mt-3 pt-3 border-t border-gray-200">
            {/* 自然语言摘要 */}
            {naturalSummary && (
              <div className="text-sm text-gray-600 bg-gray-50 p-3 rounded-lg leading-relaxed">
                <span className="font-medium text-gray-700">💡 思考过程：</span>
                {naturalSummary}
              </div>
            )}

            {/* 按钮行：展开按钮 + 一键复制（同一行） */}
            <div className="flex items-center gap-3 mt-2">
              <button
                onClick={() => setExpanded((v) => !v)}
                className="text-xs text-blue-500 hover:text-blue-700 transition-colors"
              >
                {expanded ? "📋 收起完整ReAct节点" : "📋 查看完整ReAct节点"}
              </button>
              {expanded && (
                <button
                  onClick={copyJSON}
                  className="text-xs text-gray-500 hover:text-gray-700 transition-colors"
                >
                  {copied ? "✅ 已复制" : "📋 一键复制"}
                </button>
              )}
            </div>

            {/* 可展开的 JSON */}
            {expanded && (
              <div className="relative mt-2 bg-gray-900 rounded-lg p-4 overflow-auto max-h-80">
                <pre className="text-xs text-gray-300 whitespace-pre-wrap">
                  {JSON.stringify(reactLoop, null, 2)}
                </pre>
              </div>
            )}
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
