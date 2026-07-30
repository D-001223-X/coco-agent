import type { TraceDetail, LogNode } from "../../types";

interface TraceDrawerProps {
  trace: TraceDetail | null;
  onClose: () => void;
}

export function TraceDrawer({ trace, onClose }: TraceDrawerProps) {
  if (!trace) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
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
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-gray-100 hover:bg-gray-200 flex items-center justify-center text-gray-600 transition-colors"
          >
            ✕
          </button>
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
                <span
                  className={`text-xs font-semibold ${
                    node.status === "ok" ? "text-green-600" : "text-red-500"
                  }`}
                >
                  {node.status}
                </span>
              </div>
              <div className="text-sm text-gray-600 mb-2">
                <span className="font-semibold">服务:</span> {node.service}
              </div>
              <div className="text-sm text-gray-600 mb-2">
                <span className="font-semibold">耗时:</span> {node.duration_ms} ms
              </div>
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
