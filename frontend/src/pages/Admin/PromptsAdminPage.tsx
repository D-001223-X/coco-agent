import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AdminLayout } from "../../components/Layout/AdminLayout";
import { Card, ErrorText, Loading, SuccessText } from "../../components/UI/AdminUI";
import {
  fetchPrompts,
  fetchRefusePhrases,
  updateRefusePhrase,
} from "../../api/admin";
import type { PromptInfo, RefusePhrase } from "../../types";

const PROMPT_META: Record<string, { desc: string; icon: string }> = {
  intent: { desc: "意图识别：判断 SUPPORT / FEEDBACK / CHAT", icon: "🧠" },
  support: { desc: "客服回答：基于知识库回答产品咨询", icon: "📖" },
  chat: { desc: "闲聊回复：友好轻松的日常对话", icon: "💬" },
  feedback: { desc: "反馈处理：回应用户建议和反馈", icon: "✉️" },
  plan: { desc: "计划生成：AI 学习计划生成", icon: "🗺️" },
  roleplay: { desc: "角色扮演：场景对话 Skill", icon: "🎭" },
  freechat: { desc: "自由对话：自然交流 Skill", icon: "💬" },
  topic: { desc: "话题讨论：深度讨论 Skill", icon: "📝" },
  feedback_report: { desc: "智能反馈：学习报告生成", icon: "📊" },
  bad_case: { desc: "数据飞轮：Bad Case 处理与知识草稿", icon: "🔄" },
};

export default function PromptsAdminPage() {
  const [prompts, setPrompts] = useState<PromptInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Refusal phrase config state
  const [refuse, setRefuse] = useState<Record<string, RefusePhrase>>({});
  const [refuseEdits, setRefuseEdits] = useState<Record<string, string>>({});
  const [savingKey, setSavingKey] = useState("");
  const [success, setSuccess] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([fetchPrompts(), fetchRefusePhrases()])
      .then(([p, r]) => {
        setPrompts(p);
        setRefuse(r);
        const edits: Record<string, string> = {};
        Object.values(r).forEach((item) => {
          edits[item.key] = item.value;
        });
        setRefuseEdits(edits);
        setError("");
      })
      .catch(() => setError("加载数据失败"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleSaveRefuse = async (key: string) => {
    setSavingKey(key);
    setError("");
    try {
      await updateRefusePhrase(key, refuseEdits[key] ?? "");
      setSuccess("拒答话术已保存，即时生效");
      setTimeout(() => setSuccess(""), 2500);
      load();
    } catch (e) {
      setError("保存失败");
    } finally {
      setSavingKey("");
    }
  };

  return (
    <AdminLayout>
      <div className="max-w-4xl mx-auto space-y-5">
        <h2 className="text-xl font-bold text-gray-800">提示词管理</h2>
        <ErrorText text={error} />
        <SuccessText text={success} />
        {loading ? (
          <Loading />
        ) : (
          <>
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

            {/* 拒答话术配置 */}
            <Card title="拒答话术（useful=false 时展示的固定文案）">
              <div className="space-y-4">
                {Object.entries(refuse).map(([key, item]) => (
                  <div key={key}>
                    <div className="flex items-center justify-between mb-1">
                      <div>
                        <span className="text-sm font-semibold text-gray-800">
                          {item.description || key}
                        </span>
                        <span className="text-xs text-gray-400 ml-2 font-mono">
                          {key}
                        </span>
                      </div>
                      <button
                        onClick={() => handleSaveRefuse(key)}
                        disabled={savingKey === key}
                        className="px-4 py-1.5 rounded-button bg-coral hover:bg-coral-hover text-white text-xs font-semibold disabled:opacity-50"
                      >
                        {savingKey === key ? "保存中..." : "保存"}
                      </button>
                    </div>
                    <input
                      value={refuseEdits[key] ?? ""}
                      onChange={(e) =>
                        setRefuseEdits((prev) => ({ ...prev, [key]: e.target.value }))
                      }
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-coral/30"
                    />
                  </div>
                ))}
              </div>
              <p className="text-xs text-gray-400 mt-3">
                💡 修改后即时生效：知识库未覆盖时返回「{refuse.refuse_uncovered?.value ?? "暂时不能回答这个问题"}」
              </p>
            </Card>
          </>
        )}
      </div>
    </AdminLayout>
  );
}
