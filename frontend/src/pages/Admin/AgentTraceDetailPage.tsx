import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AdminLayout } from "../../components/Layout/AdminLayout";
import { fetchAgentTraceDetail, type AgentTraceDetail } from "../../api/admin";

const NODE_META: Record<string, { label: string; color: string }> = {
  agent_decision: { label: "决策层", color: "bg-coral/10 text-coral" },
  react_loop: { label: "ReAct 循环", color: "bg-blue-50 text-blue-700" },
  multi_agent: { label: "多 Agent", color: "bg-purple-50 text-purple-700" },
  reflection: { label: "反思", color: "bg-amber-50 text-amber-700" },
  intent_recognition: { label: "意图识别", color: "bg-green-50 text-green-700" },
};

export default function AgentTraceDetailPage() {
  const { traceId = "" } = useParams();
  const [trace, setTrace] = useState<AgentTraceDetail | null>(null);
  const [expanded, setExpanded] = useState<Set<number>>(new Set([0]));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const data = await fetchAgentTraceDetail(traceId);
        setTrace(data);
      } catch (e) {
        setError("轨迹加载失败");
      } finally {
        setLoading(false);
      }
    })();
  }, [traceId]);

  const toggleNode = (i: number) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });
  };

  return (
    <AdminLayout>
      <div className="p-6 max-w-4xl">
        <div className="flex items-center gap-3 mb-6">
          <Link to="/admin/agent/traces" className="text-coral hover:underline text-sm">
            ← 返回列表
          </Link>
          <h1 className="text-2xl font-bold text-gray-800">🤖 决策轨迹详情</h1>
          <span className="text-xs text-gray-400 font-mono truncate">{traceId}</span>
        </div>

        {loading && <p className="text-gray-400 text-sm">加载中...</p>}
        {error && <p className="text-coral text-sm">{error}</p>}

        {trace && (
          <>
            {/* 概览 */}
            <div className="bg-white rounded-card border border-gray-100 shadow-sm p-5 mb-6">
              <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
                <span className="text-gray-700">
                  <span className="text-gray-400">用户输入：</span>
                  {trace.query}
                </span>
                <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
                  {trace.mode}
                </span>
                <span
                  className={`text-xs px-2 py-0.5 rounded-full ${
                    trace.status === "success"
                      ? "bg-green-50 text-green-700"
                      : "bg-red-50 text-red-700"
                  }`}
                >
                  {trace.status}
                </span>
                <span className="text-xs text-gray-400">
                  总耗时 {trace.total_duration_ms}ms
                </span>
              </div>

              {/* 决策路径可视化 */}
              <div className="mt-5">
                <p className="text-xs font-semibold text-gray-500 mb-2">决策路径</p>
                <div className="flex items-center gap-2 flex-wrap">
                  {trace.decision_path.map((node, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <span
                        className={`px-3 py-1 rounded-full text-xs font-semibold ${
                          NODE_META[node.node]?.color ?? "bg-gray-100 text-gray-600"
                        }`}
                      >
                        {NODE_META[node.node]?.label ?? node.node}
                        <span className="ml-1 opacity-60">· {node.duration_ms}ms</span>
                      </span>
                      {i < trace.decision_path.length - 1 && (
                        <span className="text-gray-300">→</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* 节点详情 */}
            {trace.decision_path.map((node, i) => (
              <div key={i} className="bg-white rounded-card border border-gray-100 shadow-sm p-5 mb-4">
                <div
                  className="flex items-center justify-between cursor-pointer"
                  onClick={() => toggleNode(i)}
                >
                  <div className="flex items-center gap-3">
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-semibold ${
                        NODE_META[node.node]?.color ?? "bg-gray-100 text-gray-600"
                      }`}
                    >
                      {NODE_META[node.node]?.label ?? node.node}
                    </span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full ${
                        node.status === "ok"
                          ? "bg-green-50 text-green-700"
                          : "bg-red-50 text-red-700"
                      }`}
                    >
                      {node.status}
                    </span>
                    {node.service && (
                      <span className="text-xs text-gray-400">{node.service}</span>
                    )}
                    <span className="text-xs text-gray-400">{node.duration_ms}ms</span>
                  </div>
                  <span className="text-gray-400 text-xs">
                    {expanded.has(i) ? "▲ 收起" : "▼ 展开"}
                  </span>
                </div>

                {expanded.has(i) && (
                  <div className="mt-4 grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <div>
                      <h4 className="text-xs font-medium text-gray-500 mb-1.5">输入</h4>
                      <pre className="bg-warmwhite p-3 rounded-lg text-xs overflow-auto max-h-48 text-gray-700">
                        {JSON.stringify(node.input, null, 2)}
                      </pre>
                    </div>
                    <div>
                      <h4 className="text-xs font-medium text-gray-500 mb-1.5">输出</h4>
                      <pre className="bg-warmwhite p-3 rounded-lg text-xs overflow-auto max-h-48 text-gray-700">
                        {JSON.stringify(node.output, null, 2)}
                      </pre>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </>
        )}
      </div>
    </AdminLayout>
  );
}
