import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AdminLayout } from "../../components/Layout/AdminLayout";
import {
  Badge,
  Card,
  ErrorText,
  Loading,
  SuccessText,
} from "../../components/UI/AdminUI";
import {
  fetchBadCase,
  generateBadCaseDraft,
  storeBadCase,
  updateBadCase,
} from "../../api/admin";
import type { BadCase } from "../../types";

export default function BadCaseDetailPage() {
  const { id = "" } = useParams();
  const badCaseId = Number(id);
  const [badCase, setBadCase] = useState<BadCase | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [idealAnswer, setIdealAnswer] = useState("");
  const [draft, setDraft] = useState("");
  const [generating, setGenerating] = useState(false);
  const [storing, setStoring] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const b = await fetchBadCase(badCaseId);
      setBadCase(b);
      setIdealAnswer(b.ideal_answer ?? "");
      setDraft(b.ideal_answer ?? "");
      setError("");
    } catch (e) {
      setError("加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (badCaseId) load();
  }, [badCaseId]);

  const handleSaveIdeal = async () => {
    try {
      const updated = await updateBadCase(badCaseId, { ideal_answer: idealAnswer });
      setBadCase(updated);
      setSuccess("已保存理想答案，状态 → 已校准");
      setTimeout(() => setSuccess(""), 2500);
    } catch (e) {
      setError("保存失败");
    }
  };

  const handleIgnore = async () => {
    if (!window.confirm("确定忽略此 Bad Case？")) return;
    try {
      const updated = await updateBadCase(badCaseId, { status: "ignored" });
      setBadCase(updated);
      setSuccess("已标记为忽略");
    } catch (e) {
      setError("操作失败");
    }
  };

  const handleGenerate = async () => {
    setGenerating(true);
    setError("");
    try {
      const d = await generateBadCaseDraft(badCaseId);
      setDraft(d);
      setSuccess("AI 草稿已生成");
    } catch (e) {
      setError("生成草稿失败");
    } finally {
      setGenerating(false);
    }
  };

  const handleStore = async () => {
    if (!window.confirm("确定将草稿保存到知识库并重建索引吗？")) return;
    setStoring(true);
    setError("");
    try {
      await storeBadCase(badCaseId);
      setSuccess("已入库并重建索引，状态 → 已入库");
      load();
    } catch (e) {
      setError("入库失败");
    } finally {
      setStoring(false);
    }
  };

  if (loading) {
    return (
      <AdminLayout>
        <Loading />
      </AdminLayout>
    );
  }

  if (!badCase) {
    return (
      <AdminLayout>
        <p className="text-gray-400 text-center py-12">Bad Case 不存在</p>
      </AdminLayout>
    );
  }

  const statusColor =
    badCase.status === "stored"
      ? "green"
      : badCase.status === "calibrated"
      ? "blue"
      : badCase.status === "ignored"
      ? "gray"
      : "amber";

  return (
    <AdminLayout>
      <div className="max-w-3xl mx-auto space-y-5">
        <div className="flex items-center gap-3">
          <Link to="/admin/bad-cases" className="text-sm text-gray-500 hover:text-coral">
            ← 返回
          </Link>
          <h2 className="text-xl font-bold text-gray-800">
            Bad Case #{badCase.id}
          </h2>
          <Badge color={statusColor as "green" | "blue" | "gray" | "amber"}>
            {badCase.status}
          </Badge>
          <Badge color={badCase.source === "auto" ? "amber" : "blue"}>
            {badCase.source === "auto" ? "自动收集" : "手动标记"}
          </Badge>
        </div>

        <ErrorText text={error} />
        <SuccessText text={success} />

        {/* 原始信息 */}
        <Card title="原始信息">
          <div className="space-y-3">
            <div>
              <p className="text-xs text-gray-400 mb-1">用户问题</p>
              <p className="text-sm text-gray-800 bg-warmwhite/60 rounded-lg p-3">
                {badCase.user_question}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-1">系统回答</p>
              <p className="text-sm text-gray-600 bg-warmwhite/60 rounded-lg p-3">
                {badCase.system_answer || "（无）"}
              </p>
            </div>
            <div className="flex gap-4 text-xs text-gray-400">
              <span>意图: {badCase.intent || "-"}</span>
              <span>trace: {badCase.trace_id?.slice(0, 16) || "-"}...</span>
              <span>
                创建: {new Date(badCase.created_at).toLocaleString("zh-CN")}
              </span>
            </div>
          </div>
        </Card>

        {/* 校准 */}
        <Card title="校准（理想答案）">
          <textarea
            value={idealAnswer}
            onChange={(e) => setIdealAnswer(e.target.value)}
            rows={4}
            className="w-full p-3 border border-gray-200 rounded-lg text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-coral/30"
            placeholder="填写该问题的理想回答..."
          />
          <div className="flex gap-2 mt-3">
            <button
              onClick={handleSaveIdeal}
              className="px-4 py-2 rounded-button bg-coral hover:bg-coral-hover text-white text-sm font-semibold"
            >
              保存理想答案
            </button>
            <button
              onClick={handleIgnore}
              className="px-4 py-2 rounded-button text-sm font-semibold text-gray-500 border border-gray-200 hover:bg-gray-50"
            >
              忽略
            </button>
          </div>
        </Card>

        {/* AI 生成 */}
        <Card title="AI 生成知识草稿">
          <div className="flex gap-2 mb-3">
            <button
              onClick={handleGenerate}
              disabled={generating}
              className="px-4 py-2 rounded-button bg-warmorange text-white text-sm font-semibold disabled:opacity-50"
            >
              {generating ? "生成中..." : "🤖 AI 生成草稿"}
            </button>
            <button
              onClick={handleStore}
              disabled={storing || !draft}
              className="px-4 py-2 rounded-button bg-green-600 hover:bg-green-700 text-white text-sm font-semibold disabled:opacity-50"
            >
              {storing ? "入库中..." : "保存并入库"}
            </button>
          </div>
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={8}
            className="w-full p-3 border border-gray-200 rounded-lg text-sm font-mono text-gray-800 focus:outline-none focus:ring-2 focus:ring-coral/30 bg-warmwhite/50"
            placeholder="点击『AI 生成草稿』自动生成，或手动编辑..."
          />
          <p className="text-xs text-gray-400 mt-2">
            入库流程：写入 knowledge_base/coco_knowledge.md → 自动重建索引 → 状态更新为「已入库」
          </p>
        </Card>
      </div>
    </AdminLayout>
  );
}
