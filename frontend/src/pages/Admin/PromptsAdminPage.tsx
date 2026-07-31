import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AdminLayout } from "../../components/Layout/AdminLayout";
import { Card, ErrorText, Loading } from "../../components/UI/AdminUI";
import { fetchPrompts } from "../../api/admin";
import type { PromptInfo } from "../../types";

const PROMPT_META: Record<string, { desc: string; icon: string }> = {
  intent: { desc: "意图识别：判断 SUPPORT / FEEDBACK / CHAT", icon: "🧠" },
  support: { desc: "客服回答：基于知识库生成回答", icon: "📖" },
  chat: { desc: "闲聊回复：友好轻松的日常对话", icon: "💬" },
};

export default function PromptsAdminPage() {
  const [prompts, setPrompts] = useState<PromptInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchPrompts()
      .then((data) => {
        setPrompts(data);
        setError("");
      })
      .catch(() => setError("加载提示词失败"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <AdminLayout>
      <div className="max-w-4xl mx-auto space-y-5">
        <h2 className="text-xl font-bold text-gray-800">提示词管理</h2>
        <ErrorText text={error} />
        {loading ? (
          <Loading />
        ) : (
          <div className="grid md:grid-cols-3 gap-4">
            {prompts.map((p) => {
              const meta = PROMPT_META[p.name] ?? { desc: "", icon: "📝" };
              return (
                <Link key={p.name} to={`/admin/prompts/${p.name}`}>
                  <Card className="hover:shadow-md transition-shadow cursor-pointer h-full">
                    <div className="flex items-start justify-between mb-3">
                      <span className="text-3xl">{meta.icon}</span>
                      <span className="text-xs bg-gray-100 text-gray-500 px-2 py-1 rounded-full">
                        v{p.version}
                      </span>
                    </div>
                    <h3 className="text-base font-semibold text-gray-800 mb-1">
                      {p.name}
                    </h3>
                    <p className="text-xs text-gray-400 mb-3">{meta.desc}</p>
                    <p className="text-xs text-gray-500 line-clamp-3 bg-gray-50 rounded-lg p-2">
                      {p.content.slice(0, 80)}...
                    </p>
                  </Card>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </AdminLayout>
  );
}
