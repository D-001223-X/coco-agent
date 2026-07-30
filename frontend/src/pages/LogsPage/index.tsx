import { useEffect, useState } from "react";
import { MainLayout } from "../../components/Layout/MainLayout";
import { TraceDrawer } from "./TraceDrawer";
import { useLogStore } from "../../store/logStore";
import { useRequireAuth } from "../../hooks/useAuth";
import type { LogItem } from "../../types";

function formatTime(iso: string) {
  return new Date(iso).toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export default function LogsPage() {
  useRequireAuth();

  const logs = useLogStore((state) => state.logs);
  const isLoading = useLogStore((state) => state.isLoading);
  const currentTrace = useLogStore((state) => state.currentTrace);
  const loadLogs = useLogStore((state) => state.loadLogs);
  const loadTraceDetail = useLogStore((state) => state.loadTraceDetail);
  const clearCurrentTrace = useLogStore((state) => state.clearCurrentTrace);

  const [selectedTraceId, setSelectedTraceId] = useState<string | null>(null);

  useEffect(() => {
    loadLogs();
  }, [loadLogs]);

  const handleViewDetail = async (traceId: string) => {
    setSelectedTraceId(traceId);
    await loadTraceDetail(traceId);
  };

  const handleClose = () => {
    setSelectedTraceId(null);
    clearCurrentTrace();
  };

  return (
    <MainLayout>
      <div className="p-6 h-[calc(100vh-64px)] overflow-y-auto custom-scrollbar">
        <div className="max-w-5xl mx-auto">
          <h1 className="text-[22px] font-semibold text-gray-800 mb-6">历史请求日志</h1>

          {isLoading && logs.length === 0 && (
            <p className="text-gray-400">加载中...</p>
          )}

          {logs.length === 0 && !isLoading && (
            <div className="bg-white rounded-card p-10 text-center shadow-sm">
              <p className="text-gray-400">暂无日志记录</p>
            </div>
          )}

          <div className="grid gap-4">
            {logs.map((log: LogItem) => (
              <div
                key={log.id}
                className="bg-white rounded-card p-5 shadow-sm border border-gray-100 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <p className="text-base font-semibold text-gray-800 mb-2 truncate">
                      {log.question || "无问题文本"}
                    </p>
                    <div className="flex flex-wrap items-center gap-3 text-sm text-gray-500">
                      <span className="px-2.5 py-1 rounded-full bg-warmorange/10 text-warmorange font-medium">
                        {log.intent}
                      </span>
                      <span>{formatTime(log.created_at)}</span>
                      <span className="text-gray-400 truncate max-w-[240px]">
                        trace: {log.trace_id}
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={() => handleViewDetail(log.trace_id)}
                    className="px-4 py-2 rounded-button bg-coral hover:bg-coral-hover text-white text-sm font-semibold transition-colors shadow-sm whitespace-nowrap"
                  >
                    查看详情
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <TraceDrawer
        trace={selectedTraceId ? currentTrace : null}
        onClose={handleClose}
      />
    </MainLayout>
  );
}
