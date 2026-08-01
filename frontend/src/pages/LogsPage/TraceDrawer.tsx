import { useCallback, useState } from "react";
import type { TraceDetail, LogNode } from "../../types";
import { copyText, jsonStringifyPretty } from "../../utils/clipboard";
import { Toast } from "../../components/UI/Toast";

interface TraceDrawerProps {
  trace: TraceDetail | null;
  onClose: () => void;
}

interface RetrievalHit {
  chunk_id?: string;
  doc_index?: number;
  rrf_score?: number;
  faiss_score?: number | null;
  bm25_score?: number | null;
  rerank_score?: number | null;
  section?: string;
  content_preview?: string;
}

function RetrievalNodeDetail({ node }: { node: LogNode }) {
  const [expanded, setExpanded] = useState(false);
  const output = (node.output_data ?? {}) as {
    count?: number;
    results?: RetrievalHit[];
    result_count?: number;
  };
  const hits: RetrievalHit[] =
    node.node === "rerank"
      ? (output.results ?? []).map((r) => ({
          chunk_id: String(r.doc_index ?? "?"),
          rerank_score: r.rerank_score,
        }))
      : output.results ?? [];

  if (hits.length === 0) return null;

  return (
    <div className="bg-white rounded-input p-3 border border-gray-100">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center justify-between text-xs font-semibold text-gray-500"
      >
        <span>命中片段 ({hits.length})</span>
        <span>{expanded ? "收起 ▲" : "展开 ▼"}</span>
      </button>
      {expanded && (
        <ul className="mt-3 space-y-2">
          {hits.map((hit, i) => (
            <li key={i} className="border border-gray-100 rounded-lg p-2">
              <div className="flex items-center gap-2 flex-wrap text-[11px] text-gray-600">
                <span className="bg-coral/10 text-coral px-1.5 py-0.5 rounded font-mono">
                  #{hit.chunk_id}
                </span>
                {hit.section && (
                  <span className="text-gray-500 truncate max-w-[180px]">
                    {hit.section}
                  </span>
                )}
                {hit.rrf_score !== undefined && (
                  <span className="bg-gray-100 px-1.5 py-0.5 rounded">
                    RRF: {hit.rrf_score}
                  </span>
                )}
                {hit.faiss_score !== undefined && hit.faiss_score !== null && (
                  <span className="bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded">
                    FAISS: {hit.faiss_score}
                  </span>
                )}
                {hit.bm25_score !== undefined && hit.bm25_score !== null && (
                  <span className="bg-amber-50 text-amber-700 px-1.5 py-0.5 rounded">
                    BM25: {hit.bm25_score}
                  </span>
                )}
                {hit.rerank_score !== undefined && hit.rerank_score !== null && (
                  <span className="bg-green-50 text-green-700 px-1.5 py-0.5 rounded">
                    RERANK: {hit.rerank_score}
                  </span>
                )}
              </div>
              {hit.content_preview && (
                <p className="mt-1.5 text-[11px] text-gray-500 leading-relaxed">
                  {hit.content_preview}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ── Copy helpers ────────────────────────────────────────
function buildNodeJson(node: LogNode): string {
  return jsonStringifyPretty({
    node: node.node,
    service: node.service,
    duration_ms: node.duration_ms,
    status: node.status,
    input: node.input_data,
    output: node.output_data,
  });
}

function buildTraceMarkdown(trace: TraceDetail): string {
  const parts: string[] = [];
  parts.push("# 链路详情");
  parts.push(`trace_id: ${trace.trace_id}`);
  parts.push("");
  for (const node of trace.nodes) {
    parts.push(`## ${node.node}`);
    parts.push(`服务: ${node.service} | 耗时: ${node.duration_ms} ms | 状态: ${node.status}`);
    parts.push("");
    parts.push("### 输入");
    parts.push("```json");
    parts.push(jsonStringifyPretty(node.input_data));
    parts.push("```");
    parts.push("");
    parts.push("### 输出");
    parts.push("```json");
    parts.push(jsonStringifyPretty(node.output_data));
    parts.push("```");
    parts.push("");
  }
  return parts.join("\n");
}

export function TraceDrawer({ trace, onClose }: TraceDrawerProps) {
  const [toast, setToast] = useState<string | null>(null);
  const [copyingAll, setCopyingAll] = useState(false);

  const showToast = useCallback((msg: string) => {
    setToast(null);
    // 用 rAF 确保 Toast 组件重新挂载，连续点击也能触发动画
    requestAnimationFrame(() => setToast(msg));
  }, []);

  if (!trace) return null;

  const handleCopyAll = async () => {
    setCopyingAll(true);
    const ok = await copyText(buildTraceMarkdown(trace));
    setCopyingAll(false);
    showToast(ok ? "已复制全部链路" : "复制失败，请手动复制");
  };

  const handleCopyNode = async (node: LogNode) => {
    const ok = await copyText(buildNodeJson(node));
    showToast(ok ? `已复制 ${node.node} 节点` : "复制失败，请手动复制");
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <Toast message={toast} onDismiss={() => setToast(null)} />
      <div
        className="absolute inset-0 bg-black/30"
        onClick={onClose}
        role="presentation"
      />
      <div className="relative w-full max-w-lg h-full bg-white shadow-2xl animate-message-in overflow-y-auto custom-scrollbar">
        <div className="sticky top-0 bg-white border-b border-gray-100 p-5 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-gray-800">链路详情</h2>
            <p className="text-xs text-gray-500 mt-1">trace_id: {trace.trace_id}</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleCopyAll}
              disabled={copyingAll}
              className="px-3 py-1.5 rounded-button bg-coral hover:bg-coral-hover text-white text-xs font-semibold disabled:opacity-50 transition-colors"
            >
              {copyingAll ? "复制中..." : "⧉ 复制全部"}
            </button>
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-full bg-gray-100 hover:bg-gray-200 flex items-center justify-center text-gray-600 transition-colors"
            >
              ✕
            </button>
          </div>
        </div>

        <div className="p-5 space-y-4">
          {trace.nodes.map((node: LogNode, index: number) => (
            <div
              key={index}
              className="rounded-card border border-gray-100 bg-warmwhite p-4 shadow-sm"
            >
              <div className="flex items-center justify-between mb-3">
                <span className="px-3 py-1 rounded-full text-xs font-semibold bg-coral/10 text-coral">
                  {node.node}
                </span>
                <div className="flex items-center gap-2">
                  <span
                    className={`text-xs font-semibold ${
                      node.status === "ok" ? "text-green-600" : "text-red-500"
                    }`}
                  >
                    {node.status}
                  </span>
                  <button
                    onClick={() => handleCopyNode(node)}
                    className="text-xs px-2 py-1 rounded-button text-gray-500 border border-gray-200 hover:bg-coral/10 hover:text-coral hover:border-coral/30 transition-colors"
                    title={`复制 ${node.node} 节点`}
                  >
                    ⧉ 复制
                  </button>
                </div>
              </div>
              <div className="text-sm text-gray-600 mb-2">
                <span className="font-semibold">服务:</span> {node.service}
              </div>
              <div className="text-sm text-gray-600 mb-2">
                <span className="font-semibold">耗时:</span> {node.duration_ms} ms
              </div>

              {/* 命中片段（retrieval / rerank 节点） */}
              {(node.node === "retrieval" || node.node === "rerank") && (
                <div className="mt-3">
                  <RetrievalNodeDetail node={node} />
                </div>
              )}

              <div className="grid grid-cols-1 gap-3 mt-3">
                <div className="bg-white rounded-input p-3 border border-gray-100">
                  <p className="text-xs font-semibold text-gray-500 mb-1">输入</p>
                  <pre className="text-xs text-gray-700 overflow-x-auto whitespace-pre-wrap">
                    {JSON.stringify(node.input_data, null, 2)}
                  </pre>
                </div>
                <div className="bg-white rounded-input p-3 border border-gray-100">
                  <p className="text-xs font-semibold text-gray-500 mb-1">输出</p>
                  <pre className="text-xs text-gray-700 overflow-x-auto whitespace-pre-wrap">
                    {JSON.stringify(node.output_data, null, 2)}
                  </pre>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
