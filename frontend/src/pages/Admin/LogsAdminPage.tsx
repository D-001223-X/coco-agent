import { useEffect, useState } from "react";
import { AdminLayout } from "../../components/Layout/AdminLayout";
import {
  Badge,
  Card,
  Empty,
  ErrorText,
  Loading,
} from "../../components/UI/AdminUI";
import { fetchDashboard, markBadCase } from "../../api/admin";
import { fetchLogs } from "../../api/logs";
import type { DashboardData, LogItem } from "../../types";

export default function LogsAdminPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [logs, setLogs] = useState<LogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const [d, l] = await Promise.all([fetchDashboard(), fetchLogs()]);
      setData(d);
      setLogs(l);
      setError("");
    } catch (e) {
      setError("加载看板失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleMarkBadCase = async (log: LogItem) => {
    if (!window.confirm(`将 trace ${log.trace_id.slice(0, 12)}... 标记为 Bad Case？`)) return;
    try {
      await markBadCase(log.trace_id);
      setSuccess("已标记为 Bad Case");
      setTimeout(() => setSuccess(""), 2000);
    } catch (e) {
      setError("标记失败");
    }
  };

  const intentColors: Record<string, string> = {
    SUPPORT: "bg-coral/10 text-coral",
    FEEDBACK: "bg-amber-50 text-amber-700",
    CHAT: "bg-green-50 text-green-700",
  };

  if (loading) {
    return (
      <AdminLayout>
        <Loading />
      </AdminLayout>
    );
  }

  const metrics = data?.metrics;
  const maxTrend = Math.max(...(data?.trends.map((t) => t.requests) ?? [1]), 1);

  return (
    <AdminLayout>
      <div className="max-w-5xl mx-auto space-y-5">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-gray-800">日志分析看板</h2>
          {success && <Badge color="green">{success}</Badge>}
        </div>
        <ErrorText text={error} />

        {/* 指标卡片 */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="text-center">
            <p className="text-3xl font-bold text-coral">{metrics?.today_requests ?? 0}</p>
            <p className="text-xs text-gray-400 mt-1">今日请求</p>
          </Card>
          <Card className="text-center">
            <p className="text-3xl font-bold text-warmorange">
              {metrics?.refusal_rate ?? 0}%
            </p>
            <p className="text-xs text-gray-400 mt-1">拒答率</p>
          </Card>
          <Card className="text-center">
            <p className="text-3xl font-bold text-gray-800">
              {metrics?.avg_response_ms ?? 0}
            </p>
            <p className="text-xs text-gray-400 mt-1">平均响应 (ms)</p>
          </Card>
          <Card className="text-center">
            <p className="text-3xl font-bold text-gray-800">{metrics?.total_logs ?? 0}</p>
            <p className="text-xs text-gray-400 mt-1">总请求数</p>
          </Card>
        </div>

        {/* 趋势图（7天） */}
        <Card title="近 7 天请求趋势">
          {!data?.trends?.length ? (
            <Empty text="暂无趋势数据" />
          ) : (
            <div className="flex items-end gap-2 h-40">
              {data.trends.map((t) => (
                <div key={t.date} className="flex-1 flex flex-col items-center gap-1">
                  <span className="text-[10px] text-gray-400">
                    {t.requests > 0 ? t.requests : ""}
                  </span>
                  <div
                    className="w-full bg-coral/70 rounded-t-lg"
                    style={{
                      height: `${Math.max((t.requests / maxTrend) * 100, 2)}%`,
                    }}
                  />
                  <span className="text-[10px] text-gray-400">{t.date}</span>
                </div>
              ))}
            </div>
          )}
        </Card>

        <div className="grid md:grid-cols-2 gap-5">
          {/* 意图分布 */}
          <Card title="意图分布">
            {!data?.intent_distribution ||
            Object.keys(data.intent_distribution).length === 0 ? (
              <Empty text="暂无意图数据" />
            ) : (
              <div className="space-y-2">
                {Object.entries(data.intent_distribution).map(([intent, count]) => {
                  const total = Object.values(data.intent_distribution!).reduce(
                    (a, b) => a + b,
                    0
                  );
                  const pct = total ? Math.round((count / total) * 100) : 0;
                  return (
                    <div key={intent} className="flex items-center gap-2">
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs font-semibold w-20 text-center ${
                          intentColors[intent] ?? "bg-gray-100 text-gray-600"
                        }`}
                      >
                        {intent}
                      </span>
                      <div className="flex-1 h-5 bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-coral rounded-full"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-500 w-14 text-right">
                        {count} ({pct}%)
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </Card>

          {/* 最近日志 */}
          <Card title={`最近请求 (${logs.length})`}>
            {logs.length === 0 ? (
              <Empty text="暂无日志" />
            ) : (
              <ul className="divide-y divide-gray-50 max-h-72 overflow-y-auto">
                {logs.slice(0, 15).map((log) => (
                  <li
                    key={log.id}
                    className="py-2.5 flex items-center justify-between gap-2"
                  >
                    <div className="min-w-0">
                      <p className="text-sm text-gray-800 truncate">{log.question}</p>
                      <p className="text-xs text-gray-400">
                        {new Date(log.created_at).toLocaleString("zh-CN")}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                          intentColors[log.intent] ?? "bg-gray-100 text-gray-600"
                        }`}
                      >
                        {log.intent || "UNKNOWN"}
                      </span>
                      <button
                        onClick={() => handleMarkBadCase(log)}
                        className="text-[10px] text-coral border border-coral/30 rounded px-2 py-0.5 hover:bg-coral/5"
                      >
                        标记Bad
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>
    </AdminLayout>
  );
}
