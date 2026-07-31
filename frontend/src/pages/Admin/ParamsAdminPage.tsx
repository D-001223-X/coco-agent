import { useEffect, useState } from "react";
import { AdminLayout } from "../../components/Layout/AdminLayout";
import {
  Card,
  ErrorText,
  Loading,
  SuccessText,
} from "../../components/UI/AdminUI";
import {
  fetchParams,
  resetParams,
  saveParamsToEnv,
  updateParams,
} from "../../api/admin";
import type { ParamsInfo } from "../../types";

const PARAM_META: Array<{
  key: keyof ParamsInfo;
  label: string;
  desc: string;
  min: number;
  max: number;
  step: number;
}> = [
  { key: "faiss_top_k", label: "FAISS 检索数", desc: "向量检索候选数量", min: 5, max: 100, step: 1 },
  { key: "fts5_top_k", label: "FTS5 检索数", desc: "关键词检索候选数量", min: 5, max: 100, step: 1 },
  { key: "threshold", label: "相似度阈值", desc: "低于此分数过滤", min: 0, max: 1, step: 0.05 },
  { key: "rrf_k", label: "RRF K 值", desc: "融合平滑常数", min: 10, max: 200, step: 5 },
  { key: "final_top_k", label: "最终返回数", desc: "LLM 输入候选数", min: 1, max: 10, step: 1 },
];

export default function ParamsAdminPage() {
  const [params, setParams] = useState<ParamsInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      setParams(await fetchParams());
      setError("");
    } catch (e) {
      setError("加载参数失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleChange = async (key: keyof ParamsInfo, value: number) => {
    if (!params) return;
    const next = { ...params, [key]: value };
    setParams(next);
    setError("");
    setSuccess("");
    try {
      const updated = await updateParams({ [key]: value });
      setParams({ ...next, ...updated });
      setSuccess("参数已更新，即时生效");
    } catch (e) {
      setError("参数更新失败");
    }
  };

  const handleReset = async () => {
    if (!window.confirm("确定恢复默认参数吗？")) return;
    try {
      setParams(await resetParams());
      setSuccess("已恢复默认参数");
    } catch (e) {
      setError("重置失败");
    }
  };

  const handleSave = async () => {
    try {
      await saveParamsToEnv();
      setSuccess("参数已保存到 .env（重启后依然生效）");
    } catch (e) {
      setError("保存到 .env 失败");
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
      <div className="max-w-2xl mx-auto space-y-5">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-gray-800">检索参数调优</h2>
          <div className="flex gap-2">
            <button
              onClick={handleReset}
              className="px-4 py-2 rounded-button text-sm font-semibold text-gray-600 border border-gray-200 hover:bg-gray-50 transition-colors"
            >
              恢复默认
            </button>
            <button
              onClick={handleSave}
              className="px-4 py-2 rounded-button bg-coral hover:bg-coral-hover text-white text-sm font-semibold"
            >
              保存到 .env
            </button>
          </div>
        </div>

        <ErrorText text={error} />
        <SuccessText text={success} />

        <Card>
          <div className="space-y-6">
            {PARAM_META.map((meta) => {
              const value = params?.[meta.key] ?? 0;
              const pct = ((value - meta.min) / (meta.max - meta.min)) * 100;
              return (
                <div key={meta.key}>
                  <div className="flex items-center justify-between mb-1">
                    <div>
                      <span className="text-sm font-semibold text-gray-800">
                        {meta.label}
                      </span>
                      <span className="text-xs text-gray-400 ml-2">
                        {meta.desc}
                      </span>
                    </div>
                    <span className="text-sm font-mono font-bold text-coral">
                      {meta.step < 1 ? value.toFixed(2) : value}
                    </span>
                  </div>
                  <input
                    type="range"
                    min={meta.min}
                    max={meta.max}
                    step={meta.step}
                    value={value}
                    onChange={(e) =>
                      handleChange(meta.key, Number(e.target.value))
                    }
                    className="w-full h-2 rounded-full appearance-none cursor-pointer"
                    style={{
                      background: `linear-gradient(to right, #FF6B6B ${pct}%, #e5e7eb ${pct}%)`,
                      accentColor: "#FF6B6B",
                    }}
                  />
                  <div className="flex justify-between text-[10px] text-gray-300">
                    <span>{meta.min}</span>
                    <span>{meta.max}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </Card>

        <p className="text-xs text-gray-400">
          💡 参数修改即时生效，无需重启服务。"保存到 .env" 可将当前参数持久化，服务重启后依然生效。
        </p>
      </div>
    </AdminLayout>
  );
}
