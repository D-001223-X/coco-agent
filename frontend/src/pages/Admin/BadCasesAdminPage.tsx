import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AdminLayout } from "../../components/Layout/AdminLayout";
import {
  Badge,
  Card,
  Empty,
  ErrorText,
  Loading,
} from "../../components/UI/AdminUI";
import { fetchBadCases } from "../../api/admin";
import type { BadCase } from "../../types";

const STATUS_META: Record<string, { label: string; color: "gray" | "green" | "coral" | "blue" | "amber" }> = {
  pending: { label: "待处理", color: "amber" },
  calibrated: { label: "已校准", color: "blue" },
  stored: { label: "已入库", color: "green" },
  ignored: { label: "已忽略", color: "gray" },
};

export default function BadCasesAdminPage() {
  const [items, setItems] = useState<BadCase[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [intentFilter, setIntentFilter] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchBadCases({
        status: statusFilter || undefined,
        intent: intentFilter || undefined,
      });
      setItems(data.items);
      setTotal(data.total);
      setError("");
    } catch (e) {
      setError("加载 Bad Case 失败");
    } finally {
      setLoading(false);
    }
  }, [statusFilter, intentFilter]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <AdminLayout>
      <div className="max-w-5xl mx-auto space-y-5">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-gray-800">Bad Case 工作台</h2>
          <Badge color="coral">共 {total} 条</Badge>
        </div>

        {/* 筛选 */}
        <Card>
          <div className="flex gap-4">
            <div>
              <label className="text-xs text-gray-400 block mb-1">状态</label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-coral/30"
              >
                <option value="">全部</option>
                <option value="pending">待处理</option>
                <option value="calibrated">已校准</option>
                <option value="stored">已入库</option>
                <option value="ignored">已忽略</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-400 block mb-1">意图</label>
              <select
                value={intentFilter}
                onChange={(e) => setIntentFilter(e.target.value)}
                className="px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-coral/30"
              >
                <option value="">全部</option>
                <option value="SUPPORT">SUPPORT</option>
                <option value="FEEDBACK">FEEDBACK</option>
                <option value="CHAT">CHAT</option>
              </select>
            </div>
          </div>
        </Card>

        <ErrorText text={error} />

        {/* 列表 */}
        {loading ? (
          <Loading />
        ) : items.length === 0 ? (
          <Empty text="暂无 Bad Case" />
        ) : (
          <Card>
            <ul className="divide-y divide-gray-50">
              {items.map((b) => {
                const meta = STATUS_META[b.status] ?? STATUS_META.pending;
                return (
                  <li key={b.id} className="py-3.5">
                    <Link to={`/admin/bad-cases/${b.id}`} className="block hover:bg-warmwhite/50 rounded-lg -m-1 p-1 transition-colors">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-semibold text-gray-800">
                          #{b.id} {b.user_question}
                        </span>
                        <div className="flex items-center gap-2">
                          <Badge color={meta.color}>{meta.label}</Badge>
                          <Badge color={b.source === "auto" ? "amber" : "blue"}>
                            {b.source === "auto" ? "自动" : "手动"}
                          </Badge>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-gray-400">
                        <span>意图: {b.intent || "-"}</span>
                        <span>·</span>
                        <span>{new Date(b.created_at).toLocaleString("zh-CN")}</span>
                      </div>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </Card>
        )}
      </div>
    </AdminLayout>
  );
}
