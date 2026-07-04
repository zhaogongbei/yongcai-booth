import { useCallback, useEffect, useState } from "react";
import { motion } from "motion/react";
import { GlassCard } from "../components/GlassCard";
import { GlowBtn } from "../components/GlowBtn";
import {
  connectGoProDevice,
  disconnectGoProDevice,
  discoverGoProDevices,
  getGoProStatus,
  tokenStorage,
  type GoProDeviceResponse,
} from "../../lib/api";
import type { Screen } from "../types";

interface GoProDevice extends GoProDeviceResponse {
  status: "online" | "connecting";
}

function deviceKey(device: GoProDeviceResponse): string {
  return device.ip_address;
}

export function GoProScreen({ navigate }: { navigate: (s: Screen) => void }) {
  const [devices, setDevices] = useState<GoProDevice[]>([]);
  const [scanning, setScanning] = useState(false);
  const [connectingIp, setConnectingIp] = useState<string | null>(null);
  const [connectedDevice, setConnectedDevice] = useState<GoProDeviceResponse | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const refreshStatus = useCallback(async () => {
    const token = tokenStorage.access;
    if (!token) {
      setConnectedDevice(null);
      setMessage("请先登录后连接 GoPro");
      return;
    }

    try {
      const status = await getGoProStatus(token);
      setConnectedDevice(status.connected && status.device ? status.device : null);
      setMessage(null);
    } catch {
      setConnectedDevice(null);
      setMessage("GoPro 状态读取失败");
    }
  }, []);

  useEffect(() => {
    void refreshStatus();
  }, [refreshStatus]);

  const scanForDevices = useCallback(async () => {
    const token = tokenStorage.access;
    if (!token) {
      setMessage("请先登录后扫描 GoPro");
      setDevices([]);
      return;
    }

    setScanning(true);
    setMessage(null);
    try {
      const discovered = await discoverGoProDevices(token);
      setDevices(discovered.map((device) => ({
        ...device,
        status: device.connected ? "online" : "online",
      })));
      if (discovered.length === 0) {
        setMessage("未发现 GoPro，请确认设备已开启 WiFi 并连接到同一网络");
      }
      await refreshStatus();
    } catch {
      setDevices([]);
      setMessage("GoPro 扫描失败，请确认后端服务和网络权限可用");
    } finally {
      setScanning(false);
    }
  }, [refreshStatus]);

  const connect = useCallback(async (device: GoProDevice) => {
    const token = tokenStorage.access;
    if (!token) {
      setMessage("请先登录后连接 GoPro");
      return;
    }

    setConnectingIp(device.ip_address);
    setMessage(null);
    setDevices((prev) => prev.map((item) =>
      item.ip_address === device.ip_address ? { ...item, status: "connecting" } : item
    ));

    try {
      const result = await connectGoProDevice(device, token);
      setConnectedDevice(result.device ?? device);
      setDevices((prev) => prev.map((item) => ({ ...item, status: "online" })));
    } catch {
      setMessage("连接 GoPro 失败，请检查 IP、WiFi 模式和设备授权");
      setDevices((prev) => prev.map((item) => ({ ...item, status: "online" })));
    } finally {
      setConnectingIp(null);
    }
  }, []);

  const disconnect = useCallback(async () => {
    const token = tokenStorage.access;
    if (!token) {
      setMessage("请先登录后断开 GoPro");
      return;
    }

    try {
      await disconnectGoProDevice(token);
      setConnectedDevice(null);
      setMessage(null);
    } catch {
      setMessage("断开 GoPro 失败");
    }
  }, []);

  return (
    <div className="flex-1 flex overflow-hidden">
      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-white">GoPro 摄像机</h2>
            <p className="text-xs text-white/40 mt-0.5">通过后端真实扫描和连接 GoPro WiFi 设备</p>
          </div>
          <GlowBtn size="sm" variant="ghost" onClick={() => navigate("camera")}>返回拍照</GlowBtn>
        </div>

        <div className="flex gap-3">
          <GlowBtn size="sm" variant="primary" onClick={scanForDevices} disabled={scanning || Boolean(connectingIp)}>
            {scanning ? "扫描中..." : "扫描设备"}
          </GlowBtn>
          {connectedDevice && (
            <GlowBtn size="sm" variant="outline" onClick={disconnect} disabled={Boolean(connectingIp)}>断开连接</GlowBtn>
          )}
        </div>

        {message && (
          <GlassCard className="p-4 text-xs text-amber-200">
            {message}
          </GlassCard>
        )}

        {connectedDevice && (
          <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
            <GlassCard className="p-4 border-emerald-500/30">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-emerald-500/20 flex items-center justify-center">
                  <span className="text-emerald-400 text-lg">G</span>
                </div>
                <div className="flex-1">
                  <div className="text-sm font-semibold text-white">{connectedDevice.name} (已连接)</div>
                  <div className="text-xs text-emerald-400/80">
                    IP: {connectedDevice.ip_address} | {connectedDevice.model || "GoPro"}
                  </div>
                </div>
                <GlowBtn size="sm" variant="primary" onClick={() => navigate("camera")}>
                  去拍照
                </GlowBtn>
              </div>
            </GlassCard>
          </motion.div>
        )}

        <div className="space-y-3">
          <div className="text-sm font-semibold text-white/80">发现的设备</div>
          {devices.length === 0 ? (
            <GlassCard className="p-6 text-center">
              <div className="text-sm font-semibold text-white">暂无已发现设备</div>
              <div className="mt-2 text-xs leading-5 text-white/40">
                点击扫描后只会显示后端实际发现的 GoPro，不再展示固定演示设备。
              </div>
            </GlassCard>
          ) : (
            devices.map((device) => {
              const isConnected = connectedDevice?.ip_address === device.ip_address;
              const isConnecting = connectingIp === device.ip_address || device.status === "connecting";
              return (
                <GlassCard key={deviceKey(device)} className="p-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-3 h-3 rounded-full ${isConnected ? "bg-emerald-400" : isConnecting ? "bg-yellow-400 animate-pulse" : "bg-white/30"}`} />
                    <div>
                      <div className="text-sm text-white">{device.name}</div>
                      <div className="text-xs text-white/40">{device.model || "GoPro"} - {device.ip_address}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`text-xs ${isConnected ? "text-emerald-400" : isConnecting ? "text-yellow-400" : "text-white/40"}`}>
                      {isConnected ? "已连接" : isConnecting ? "连接中..." : "已发现"}
                    </span>
                    <GlowBtn
                      size="sm"
                      variant={isConnected ? "outline" : "primary"}
                      disabled={Boolean(connectedDevice) || isConnecting}
                      onClick={() => connect(device)}
                    >
                      {isConnected ? "已连接" : "连接"}
                    </GlowBtn>
                  </div>
                </GlassCard>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
