import { useEffect, useState, type ReactNode } from "react";

const RUNTIME_API_BASE_URL = (import.meta.env.VITE_RUNTIME_API_BASE_URL ?? "http://localhost:5000/v1").replace(/\/$/, "");
const OFFLINE_ACTIVATION_ENABLED = import.meta.env.VITE_ENABLE_OFFLINE_ACTIVATION !== "false";

type LicenseStatus = {
  isActivated: boolean;
  licenseId?: string | null;
  expiresAtUtc?: string | null;
  deviceFingerprint: string;
  error?: string | null;
};

type ActivationGateProps = {
  children: ReactNode;
};

export function ActivationGate({ children }: ActivationGateProps) {
  const [status, setStatus] = useState<LicenseStatus | null>(null);
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(OFFLINE_ACTIVATION_ENABLED);

  useEffect(() => {
    if (!OFFLINE_ACTIVATION_ENABLED) return;
    void refreshStatus();
  }, []);

  async function refreshStatus() {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${RUNTIME_API_BASE_URL}/license/status`);
      const next = await response.json();
      setStatus(next);
    } catch {
      setError("无法连接本机 Runtime 授权服务，请确认 Runtime 已启动。");
      setStatus({
        isActivated: false,
        licenseId: null,
        expiresAtUtc: null,
        deviceFingerprint: "unavailable",
        error: "runtime_unavailable",
      });
    } finally {
      setLoading(false);
    }
  }

  async function activate() {
    setError(null);
    try {
      const response = await fetch(`${RUNTIME_API_BASE_URL}/license/activate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code }),
      });
      const next = await response.json();
      if (!response.ok || !next.isActivated) {
        setError(mapLicenseError(next.error));
        setStatus(next);
        return;
      }
      setStatus(next);
      setCode("");
    } catch {
      setError("激活请求失败，请确认 Runtime 已启动。");
    }
  }

  if (!OFFLINE_ACTIVATION_ENABLED) return <>{children}</>;
  if (loading && !status) {
    return (
      <div className="grid h-screen-fix place-items-center bg-[#050816] text-white">
        <div className="rounded-2xl border border-white/10 bg-white/5 px-6 py-4 text-sm text-white/70">
          正在检查本机授权状态...
        </div>
      </div>
    );
  }
  if (status?.isActivated) return <>{children}</>;

  return (
    <div className="fixed inset-0 z-[9999] grid place-items-center bg-[#050816] px-4 text-white">
      <div className="w-[560px] max-w-full rounded-3xl border border-violet-400/20 bg-[#0b1026] p-6 shadow-2xl shadow-violet-950/40">
        <div className="flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded-2xl bg-violet-500/20 text-violet-200">🔐</div>
          <div>
            <h2 className="text-lg font-semibold">激活 D-Booth Runtime</h2>
            <p className="mt-1 text-sm text-white/55">请输入为当前设备生成的离线授权码。</p>
          </div>
        </div>

        <div className="mt-5 rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <div className="text-xs text-white/45">设备指纹</div>
          <code className="mt-2 block break-all rounded-xl bg-black/30 p-3 text-xs text-violet-100">
            {status?.deviceFingerprint ?? "unknown"}
          </code>
        </div>

        <textarea
          className="mt-4 h-32 w-full resize-none rounded-2xl border border-white/10 bg-black/30 p-4 font-mono text-sm text-white outline-none transition focus:border-violet-400/60"
          value={code}
          onChange={(event) => setCode(event.target.value)}
          placeholder="输入授权码，例如 ABCDE-23456-..."
          spellCheck={false}
        />

        {(error || status?.error) && (
          <p className="mt-3 rounded-xl border border-red-400/20 bg-red-500/10 px-3 py-2 text-sm text-red-200">
            {error ?? mapLicenseError(status?.error)}
          </p>
        )}

        <div className="mt-5 flex justify-end gap-3">
          <button
            className="rounded-xl border border-white/10 px-4 py-2 text-sm text-white/70 transition hover:bg-white/5"
            onClick={refreshStatus}
            type="button"
          >
            重新检查
          </button>
          <button
            className="rounded-xl bg-violet-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-violet-400 disabled:cursor-not-allowed disabled:opacity-50"
            onClick={activate}
            disabled={!code.trim()}
            type="button"
          >
            激活
          </button>
        </div>
      </div>
    </div>
  );
}

function mapLicenseError(error?: string | null): string {
  switch (error) {
    case "not_activated":
      return "当前设备尚未激活。";
    case "device_mismatch":
      return "授权码不属于当前设备。";
    case "expired":
      return "授权码已过期。";
    case "product_mismatch":
      return "授权码不属于当前产品。";
    case "license_tampered":
      return "本地授权文件被篡改。";
    case "license_invalid":
    case "invalid_code":
      return "无效授权码。";
    case "runtime_unavailable":
      return "无法连接本机 Runtime 授权服务。";
    default:
      return error || "授权校验失败。";
  }
}
