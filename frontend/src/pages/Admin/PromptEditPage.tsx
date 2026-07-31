import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { AdminLayout } from "../../components/Layout/AdminLayout";
import {
  Badge,
  Card,
  ErrorText,
  Loading,
  SuccessText,
} from "../../components/UI/AdminUI";
import {
  fetchPrompt,
  fetchPromptHistory,
  restorePromptVersion,
  testPrompt,
  updatePrompt,
} from "../../api/admin";
import type { PromptHistoryItem } from "../../types";

export default function PromptEditPage() {
  const { name = "" } = useParams();
  const [content, setContent] = useState("");
  const [version, setVersion] = useState(0);
  const [history, setHistory] = useState<PromptHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Test state
  const [testQuestion, setTestQuestion] = useState("会员多少钱？");
  const [testResult, setTestResult] = useState("");
  const [testing, setTesting] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [p, h] = await Promise.all([
        fetchPrompt(name),
        fetchPromptHistory(name),
      ]);
      setContent(p.content);
      setVersion(p.version);
      setHistory(h);
      setError("");
    } catch (e) {
      setError("加载提示词失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (name) load();
  }, [name]);

  const handleSave = async () => {
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const r = await updatePrompt(name, content);
      setVersion(r.version);
      setSuccess(`保存成功，当前版本 v${r.version}`);
      load();
    } catch (e) {
      setError("保存失败");
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setError("");
    setSuccess("");
    setTestResult("");
    try {
      const r = await testPrompt(name, testQuestion);
      setTestResult(
        `意图: ${r.intent}\n消解后: ${r.resolved_question}\n回答: ${r.response || "（无）"}`
      );
    } catch (e) {
      setError("测试失败");
    } finally {
      setTesting(false);
    }
  };

  const handleRestore = async (item: PromptHistoryItem) => {
    if (!window.confirm(`确定恢复到 v${item.version} 吗？`)) return;
    try {
      await restorePromptVersion(name, item.version);
      setSuccess(`已恢复到 v${item.version}`);
      load();
    } catch (e) {
      setError("恢复失败");
    }
  };

  if (loading) {
    return (
      <AdminLayout>
        <Loading />
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
      <div className="max-w-4xl mx-auto space-y-5">
        <div className="flex items-center gap-3">
          <Link
            to="/admin/prompts"
            className="text-sm text-gray-500 hover:text-coral"
          >
            ← 返回
          </Link>
          <h2 className="text-xl font-bold text-gray-800">提示词：{name}</h2>
          <Badge color="blue">v{version}</Badge>
        </div>

        <ErrorText text={error} />
        <SuccessText text={success} />

        {/* 编辑区 */}
        <Card title="编辑内容（保存后即时生效）">
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={14}
            className="w-full p-3 border border-gray-200 rounded-lg text-sm font-mono text-gray-800 focus:outline-none focus:ring-2 focus:ring-coral/30 bg-warmwhite/50"
          />
          <div className="flex justify-end mt-3">
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-6 py-2.5 rounded-button bg-coral hover:bg-coral-hover text-white text-sm font-semibold disabled:opacity-50"
            >
              {saving ? "保存中..." : "保存"}
            </button>
          </div>
        </Card>

        {/* 测试区 */}
        <Card title="效果测试">
          <div className="flex gap-3">
            <input
              value={testQuestion}
              onChange={(e) => setTestQuestion(e.target.value)}
              className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-coral/30"
              placeholder="输入测试问题"
            />
            <button
              onClick={handleTest}
              disabled={testing}
              className="px-5 py-2 rounded-button bg-warmorange text-white text-sm font-semibold disabled:opacity-50"
            >
              {testing ? "测试中..." : "测试"}
            </button>
          </div>
          {testResult && (
            <pre className="mt-3 p-3 bg-gray-50 rounded-lg text-sm text-gray-700 whitespace-pre-wrap">
              {testResult}
            </pre>
          )}
        </Card>

        {/* 版本历史 */}
        <Card title={`版本历史 (${history.length})`}>
          {history.length === 0 ? (
            <p className="text-gray-400 text-sm">暂无历史版本</p>
          ) : (
            <ul className="divide-y divide-gray-50">
              {history.map((h) => (
                <li
                  key={h.id}
                  className="py-3 flex items-center justify-between gap-4"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge color="blue">v{h.version}</Badge>
                      {h.is_permanent && <Badge color="green">永久</Badge>}
                      <span className="text-xs text-gray-400">
                        {h.created_by} ·{" "}
                        {new Date(h.created_at).toLocaleString("zh-CN")}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500 truncate">{h.content.slice(0, 60)}...</p>
                  </div>
                  {h.version !== version && (
                    <button
                      onClick={() => handleRestore(h)}
                      className="shrink-0 px-3 py-1.5 rounded-button text-xs font-semibold text-gray-600 border border-gray-200 hover:bg-gray-50 transition-colors"
                    >
                      恢复
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </AdminLayout>
  );
}
