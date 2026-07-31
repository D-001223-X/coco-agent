import { useCallback, useEffect, useRef, useState } from "react";
import { AdminLayout } from "../../components/Layout/AdminLayout";
import { Badge, Card, Empty, ErrorText, Loading, SuccessText } from "../../components/UI/AdminUI";
import {
  deleteKnowledgeFile,
  fetchKnowledgeChunks,
  fetchKnowledgeFiles,
  fetchKnowledgeStatus,
  rebuildKnowledgeIndex,
  uploadKnowledgeFile,
} from "../../api/admin";
import type { KnowledgeChunk, KnowledgeFile, KnowledgeStatus } from "../../types";

export default function KnowledgeAdminPage() {
  const [files, setFiles] = useState<KnowledgeFile[]>([]);
  const [status, setStatus] = useState<KnowledgeStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [building, setBuilding] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Chunk drawer state
  const [chunks, setChunks] = useState<KnowledgeChunk[]>([]);
  const [chunksOpen, setChunksOpen] = useState(false);
  const [chunksLoading, setChunksLoading] = useState(false);
  const [expandedChunks, setExpandedChunks] = useState<Set<string>>(new Set());

  const openChunks = async () => {
    setChunksOpen(true);
    setChunksLoading(true);
    try {
      const data = await fetchKnowledgeChunks();
      setChunks(data);
    } catch (e) {
      setError("加载切块失败");
    } finally {
      setChunksLoading(false);
    }
  };

  const toggleChunk = (chunkId: string) => {
    setExpandedChunks((prev) => {
      const next = new Set(prev);
      if (next.has(chunkId)) next.delete(chunkId);
      else next.add(chunkId);
      return next;
    });
  };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [f, s] = await Promise.all([
        fetchKnowledgeFiles(),
        fetchKnowledgeStatus(),
      ]);
      setFiles(f);
      setStatus(s);
      setError("");
    } catch (e) {
      setError("加载知识库失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setError("");
    setSuccess("");
    try {
      await uploadKnowledgeFile(file);
      setSuccess(`已上传 ${file.name}`);
      if (fileInputRef.current) fileInputRef.current.value = "";
      load();
    } catch (err) {
      setError("上传失败");
    }
  };

  const handleDelete = async (filename: string) => {
    if (!window.confirm(`确定删除 ${filename} 吗？此操作不可恢复。`)) return;
    setError("");
    try {
      await deleteKnowledgeFile(filename);
      setSuccess(`已删除 ${filename}`);
      load();
    } catch (err) {
      setError("删除失败");
    }
  };

  const handleRebuild = async () => {
    if (!window.confirm("重建索引会重新解析全部知识库文档，确定继续？")) return;
    setBuilding(true);
    setError("");
    try {
      await rebuildKnowledgeIndex();
      setSuccess("索引重建完成");
      load();
    } catch (err) {
      setError("索引重建失败");
    } finally {
      setBuilding(false);
    }
  };

  const formatSize = (n: number) => (n > 1024 ? `${(n / 1024).toFixed(1)}KB` : `${n}B`);

  return (
    <AdminLayout>
      <div className="max-w-4xl mx-auto space-y-5">
        <h2 className="text-xl font-bold text-gray-800">知识库管理</h2>

        {/* 索引状态卡片 */}
        <Card>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <p className="text-2xl font-bold text-coral">{status?.chunk_count ?? "-"}</p>
              <p className="text-xs text-gray-400 mt-1">分块数量</p>
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-700 mt-2">
                {status?.last_build_at
                  ? new Date(status.last_build_at).toLocaleString("zh-CN")
                  : "未构建"}
              </p>
              <p className="text-xs text-gray-400 mt-1">最后构建时间</p>
            </div>
            <div className="flex flex-col items-center justify-center gap-2">
              <button
                onClick={handleRebuild}
                disabled={building}
                className="px-4 py-2 rounded-button bg-coral hover:bg-coral-hover text-white text-sm font-semibold disabled:opacity-50"
              >
                {building ? "构建中..." : "重建索引"}
              </button>
            </div>
          </div>
        </Card>

        <ErrorText text={error} />
        <SuccessText text={success} />

        {/* 上传区域 */}
        <Card title="上传文档">
          <div className="flex items-center gap-3">
            <input
              ref={fileInputRef}
              type="file"
              accept=".md"
              onChange={handleUpload}
              className="text-sm text-gray-600 file:mr-3 file:px-4 file:py-2 file:rounded-button file:border-0 file:bg-coral file:text-white file:text-sm file:font-semibold file:cursor-pointer"
            />
            <span className="text-xs text-gray-400">仅支持 .md 文件</span>
          </div>
        </Card>

        {/* 文件列表 */}
        <Card title={`文件列表 (${files.length})`}>
          {loading ? (
            <Loading />
          ) : files.length === 0 ? (
            <Empty text="暂无知识库文件" />
          ) : (
            <ul className="divide-y divide-gray-50">
              {files.map((f) => (
                <li
                  key={f.filename}
                  className="py-3 flex items-center justify-between"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-lg">📄</span>
                    <div>
                      <p className="text-sm font-medium text-gray-800">{f.filename}</p>
                      <p className="text-xs text-gray-400">
                        {formatSize(f.size)} ·{" "}
                        {new Date(f.modified_at).toLocaleString("zh-CN")}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {f.filename === "coco_knowledge.md" && (
                      <Badge color="green">主文件</Badge>
                    )}
                    <button
                      onClick={openChunks}
                      className="px-3 py-1.5 rounded-button text-xs font-semibold text-gray-600 border border-gray-200 hover:bg-gray-50 transition-colors"
                    >
                      查看切块
                    </button>
                    <button
                      onClick={() => handleDelete(f.filename)}
                      className="px-3 py-1.5 rounded-button text-xs font-semibold text-coral border border-coral/30 hover:bg-coral/5 transition-colors"
                    >
                      删除
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>

        {/* 切块抽屉 */}
        {chunksOpen && (
          <div className="fixed inset-0 z-50 bg-black/30 flex justify-end">
            <div className="w-full max-w-2xl bg-white h-full flex flex-col shadow-xl">
              <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
                <h3 className="text-base font-semibold text-gray-800">
                  知识库切块 ({chunks.length})
                </h3>
                <button
                  onClick={() => setChunksOpen(false)}
                  className="px-3 py-1.5 rounded-button text-sm text-gray-500 hover:bg-gray-100"
                >
                  ✕ 关闭
                </button>
              </div>
              <div className="flex-1 overflow-y-auto p-6">
                {chunksLoading ? (
                  <Loading />
                ) : chunks.length === 0 ? (
                  <Empty text="暂无切块数据（请先重建索引）" />
                ) : (
                  <ul className="space-y-3">
                    {chunks.map((c) => {
                      const expanded = expandedChunks.has(c.chunk_id);
                      return (
                        <li key={c.chunk_id} className="border border-gray-100 rounded-lg overflow-hidden">
                          <button
                            onClick={() => toggleChunk(c.chunk_id)}
                            className="w-full flex items-center justify-between px-4 py-3 hover:bg-warmwhite/60 transition-colors"
                          >
                            <div className="flex items-center gap-3 min-w-0">
                              <span className="text-xs bg-coral/10 text-coral px-2 py-0.5 rounded-full font-mono">
                                #{c.chunk_id}
                              </span>
                              <span className="text-sm text-gray-700 truncate">
                                {c.section || "（无章节）"}
                              </span>
                            </div>
                            <span className="text-xs text-gray-400 shrink-0">
                              {expanded ? "收起 ▲" : "展开 ▼"}
                            </span>
                          </button>
                          <div className="px-4 pb-3">
                            <p className="text-xs text-gray-500 bg-gray-50 rounded-lg p-3">
                              {expanded ? c.content_full : c.content_preview}
                              {!expanded && c.content_full.length > 100 && "..."}
                            </p>
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </AdminLayout>
  );
}
