import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AdminLayout } from "../../components/Layout/AdminLayout";
import {
  fetchAgentTraces,
  type AgentTraceSummary,
} from "../../api/admin";

function formatTime(iso: string): string {
  if (!iso) return "-";
  try {
    return new Date(iso).toLocaleString("zh-CN", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

const MODE_LABEL: Record<string, string> = {
  roleplay: "🎭 角色扮演",
  freechat: "💬 自由对话",
  topic: "📝 话题讨论",
  practice: "🎮 陪练",
};

const NODE_LABEL: Record<string, string> = {
  agent_decision: "决策层",
  react_loop: "ReAct 循环",
  multi_agent: "多 Agent",
  reflection: "反思",
  intent_recognition: "意图识别",
};

export default function AgentTracesPage() {
  const [traces, setTraces] = useState<AgentTraceSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [modeFilter, setModeFilter] = useState("all");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchAgentTraces(100, 0);
      setTraces(data.traces);
      setTotal(data.total);
      setError("");
    } catch (e) {
      setError("轨迹加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const filtered =
    modeFilter === "all"
      ? traces
      : traces.filter((t) => t.mode === modeFilter);

  return (
    <AdminLayout>
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-800">🤖 Agent 决策轨迹</h1>
            <p className="text-sm text-gray-500 mt-1">
              共 {total} 条 · 展示 Agent 思考过程（决策层 → ReAct 循环）
            </p>
          </div>
          <div className="flex gap-2">
            {["all", "roleplay", "freechat", "topic"].map((m) => (
              <button
                key={m}
                onClick={() => setModeFilter(m)}
                className={`px-3 py-1.5 rounded-button text-xs font-semibold transition-colors ${
                  modeFilter === m
                    ? "bg-coral text-white"
                    : "bg-white text-gray-600 border border-gray-200 hover:border-coral/40"
                }`}
              >
                {m === "all" ? "全部" : MODE_LABEL[m] ?? m}
              </button>
            ))}
          </div>
        </div>

        {error && <p className="text-sm text-coral mb-4">{error}</p>}

        <div className="bg-white rounded-card border border-gray-100 shadow-sm overflow-hidden">
          {loading ? (
            <div className="p-8 text-center text-gray-400 text-sm">加载中...</div>
          ) : filtered.length === 0 ? (
            <div className="p-8 text-center text-gray-400 text-sm">
              暂无 Agent 轨迹数据。前往陪练页面完成一次对话后刷新查看。
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-left text-xs text-gray-500">
                <tr>
                  <th className="px-4 py-3">时间</th>
                  <th className="px-4 py-3">用户输入</th>
                  <th className="px-4 py-3">模式</th>
                  <th className="px-4 py-3">决策路径</th>
                  <th className="px-4 py-3">状态</th>
                  <th className="px-4 py-3">耗时</th>
                  <th className="px-4 py-3">操作</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((trace) => (
                  <tr key={trace.trace_id} className="border-t border-gray-100 hover:bg-warmwhite/50">
                    <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
                      {formatTime(trace.created_at)}
                    </td>
                    <td className="px-4 py-3 max-w-[200px] truncate text-gray-700">
                      {trace.query}
                    </td>
                    <td className="px-4 py-3 text-xs">
                      {MODE_LABEL[trace.mode] ?? trace.mode}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-600">
                      {trace.decision_path
                        .map((n) => NODE_LABEL[n] ?? n)
                        .join(" → ")}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs ${
                          trace.status === "success"
                            ? "bg-green-50 text-green-700"
                            : "bg-red-50 text-red-700"
                        }`}
                      >
                        {trace.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">
                      {trace.total_duration_ms}ms
                    </td>
                    <td className="px-4 py-3">
                      <Link
                        to={`/admin/agent/traces/${trace.trace_id}`}
                        className="text-coral hover:underline text-xs"
                      >
                        查看详情
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </AdminLayout>
  );
}
