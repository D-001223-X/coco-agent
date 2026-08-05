import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Input } from "../../components/UI/Input";
import { Button } from "../../components/UI/Button";
import { useAuthStore } from "../../store/authStore";
import { useRedirectIfAuthenticated } from "../../hooks/useAuth";

export default function LoginPage() {
  const navigate = useNavigate();
  const login = useAuthStore((state) => state.login);
  useRedirectIfAuthenticated();

  const [email, setEmail] = useState("admin@app.com");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      await login(email, password);
      navigate("/profile", { replace: true });  // R-001：登录后回「我的」显示管理员标识
    } catch (err) {
      setError("登录失败，请检查邮箱和密码");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-warmwhite px-4">
      <div className="w-full max-w-md bg-white rounded-card shadow-xl p-8">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-gray-800 mb-2">可可语伴</h1>
          <p className="text-gray-500">AI 智能客服系统</p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          <Input
            label="邮箱"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="请输入邮箱"
            required
          />
          <Input
            label="密码"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="请输入 6 位数字密码"
            required
            minLength={6}
            maxLength={6}
          />

          {error && <p className="text-coral text-sm">{error}</p>}

          <Button type="submit" disabled={isSubmitting} className="mt-2">
            {isSubmitting ? "登录中..." : "登录"}
          </Button>
        </form>

        {/* 访客模式入口：扫码即用，无需登录 */}
        <div className="mt-6 pt-5 border-t border-gray-100 text-center">
          <p className="text-xs text-gray-400 mb-3">不想登录？扫码即用</p>
          <a
            href="/practice/assessment"
            className="inline-block w-full py-3 rounded-button bg-warmwhite border border-gray-200 text-coral text-sm font-semibold hover:border-coral/40 transition-colors"
          >
            👋 访客体验（无需注册）
          </a>
        </div>
      </div>
    </div>
  );
}
