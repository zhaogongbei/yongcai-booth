import { useState } from "react";
import { Camera, Sparkles, Mail, Lock, User as UserIcon, LogIn, LogOut, UserPlus, LayoutDashboard } from "lucide-react";
import { motion } from "motion/react";
import { toast } from "sonner";
import { GlowBtn } from "../components/GlowBtn";
import { useAuth } from "../stores/useAuth";
import { ApiError } from "../../lib/api";
import type { Screen } from "../types";

type Mode = "login" | "register";

export function LoginScreen({ navigate }: { navigate: (s: Screen) => void }) {
  const { user, login, register, logout } = useAuth();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const canSubmit = email.trim().length > 0 && password.length >= 8 && !submitting;

  const handleLogout = async () => {
    setSubmitting(true);
    try {
      await logout();
      toast.success("已登出");
    } catch {
      toast.warning("服务器端会话撤销失败，本地登录状态已清除");
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    setError(null);
    setSubmitting(true);
    try {
      if (mode === "login") {
        await login(email.trim(), password);
      } else {
        await register(email.trim(), password, fullName.trim() || undefined);
      }
      // 登录/注册成功后进入运营主页
      navigate("dashboard");
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 401) setError("邮箱或密码不正确");
        else if (err.status === 400) setError(typeof err.data === "object" && err.data && "detail" in err.data ? String((err.data as Record<string, unknown>).detail) : "请求无效，请检查输入");
        else if (err.status === 409) setError("该邮箱已注册，请直接登录");
        else setError(err.message || "操作失败，请重试");
      } else {
        setError(err instanceof Error ? err.message : "网络错误，请稍后重试");
      }
    } finally {
      setSubmitting(false);
    }
  };

  // 已登录：展示当前账户与登出/进入主页入口，而非空登录表单
  if (user) {
    const label = user.full_name?.trim() || user.email;
    return (
      <div className="relative w-full h-full flex items-center justify-center overflow-hidden p-6" style={{ background: "#050816" }}>
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] rounded-full"
            style={{ background: "radial-gradient(ellipse, rgba(139,92,246,0.16) 0%, rgba(59,130,246,0.07) 50%, transparent 70%)" }} />
        </div>
        <motion.div
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}
          className="relative z-10 w-full max-w-sm text-center space-y-5"
        >
          <div className="w-16 h-16 mx-auto rounded-full bg-gradient-to-br from-violet-500 to-pink-500 flex items-center justify-center text-2xl font-bold text-white">
            {label.charAt(0).toUpperCase()}
          </div>
          <div>
            <div className="text-sm font-semibold text-white">{label}</div>
            <div className="text-xs text-white/40 mt-0.5">{user.email}</div>
          </div>
          <div className="space-y-2">
            <GlowBtn variant="primary" size="md" className="w-full justify-center" onClick={() => navigate("dashboard")}>
              <LayoutDashboard size={15} />进入运营主页
            </GlowBtn>
            <GlowBtn variant="ghost" size="md" className="w-full justify-center" disabled={submitting} onClick={() => void handleLogout()}>
              <LogOut size={15} />{submitting ? "登出中..." : "登出"}
            </GlowBtn>
          </div>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full flex items-center justify-center overflow-hidden p-6" style={{ background: "#050816" }}>
      {/* Nebula background */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] rounded-full"
          style={{ background: "radial-gradient(ellipse, rgba(139,92,246,0.16) 0%, rgba(59,130,246,0.07) 50%, transparent 70%)" }} />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}
        className="relative z-10 w-full max-w-sm"
      >
        {/* Logo */}
        <div className="flex flex-col items-center gap-3 mb-8">
          <div className="relative w-16 h-16 rounded-2xl flex items-center justify-center"
            style={{ background: "linear-gradient(135deg, #7c3aed 0%, #8b5cf6 50%, #a78bfa 100%)", boxShadow: "0 0 40px rgba(139,92,246,0.5)" }}>
            <Camera size={30} className="text-white" />
            <div className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-gradient-to-br from-pink-400 to-pink-600 flex items-center justify-center">
              <Sparkles size={10} className="text-white" />
            </div>
          </div>
          <div className="text-center">
            <div className="flex items-baseline gap-1.5 justify-center">
              <span className="text-2xl font-bold bg-clip-text text-transparent" style={{ backgroundImage: "linear-gradient(135deg, #a78bfa 0%, #8b5cf6 40%, #ec4899 100%)" }}>AI</span>
              <span className="text-2xl font-bold text-white">Booth</span>
            </div>
            <p className="text-xs text-white/40 mt-1">{mode === "login" ? "登录以管理活动与拍摄" : "创建账户开始使用"}</p>
          </div>
        </div>

        {/* Mode tabs */}
        <div className="flex gap-1 p-1 rounded-xl bg-white/5 border border-white/10 mb-5">
          {(["login", "register"] as Mode[]).map(m => (
            <button
              key={m}
              type="button"
              onClick={() => { setMode(m); setError(null); }}
              className={`flex-1 py-2 rounded-lg text-xs font-medium transition-colors ${mode === m ? "bg-violet-500/25 text-violet-200" : "text-white/50 hover:text-white/80"}`}
            >
              {m === "login" ? "登录" : "注册"}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          {mode === "register" && (
            <div className="relative">
              <UserIcon size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30" />
              <input
                type="text"
                value={fullName}
                onChange={e => setFullName(e.target.value)}
                placeholder="姓名（选填）"
                autoComplete="name"
                className="w-full bg-white/5 border border-white/10 rounded-xl pl-9 pr-3 py-2.5 text-sm text-white placeholder:text-white/30 outline-none focus:border-violet-500/50"
              />
            </div>
          )}
          <div className="relative">
            <Mail size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30" />
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="邮箱"
              autoComplete="email"
              required
              className="w-full bg-white/5 border border-white/10 rounded-xl pl-9 pr-3 py-2.5 text-sm text-white placeholder:text-white/30 outline-none focus:border-violet-500/50"
            />
          </div>
          <div className="relative">
            <Lock size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30" />
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="密码（至少 8 位）"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              required
              minLength={8}
              className="w-full bg-white/5 border border-white/10 rounded-xl pl-9 pr-3 py-2.5 text-sm text-white placeholder:text-white/30 outline-none focus:border-violet-500/50"
            />
          </div>

          {error && (
            <div className="text-xs text-red-300 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
              {error}
            </div>
          )}

          <GlowBtn type="submit" variant="primary" size="md" disabled={!canSubmit} className="w-full justify-center mt-1">
            {mode === "login" ? <LogIn size={15} /> : <UserPlus size={15} />}
            {submitting ? "处理中..." : mode === "login" ? "登录" : "注册并登录"}
          </GlowBtn>
        </form>

        <button
          type="button"
          onClick={() => navigate("attract")}
          className="w-full text-center text-xs text-white/30 hover:text-white/60 transition-colors mt-5"
        >
          稍后再说，进入欢迎屏
        </button>
      </motion.div>
    </div>
  );
}
