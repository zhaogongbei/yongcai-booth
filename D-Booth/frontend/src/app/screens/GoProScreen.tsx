import { useState } from "react";
import { motion } from "motion/react";
import { GlassCard } from "../components/GlassCard";
import { GlowBtn } from "../components/GlowBtn";
import type { Screen } from "../types";

interface GoProDevice {
  name: string;
  ip: string;
  model: string;
  status: "online" | "offline" | "connecting";
}

const DEMO_DEVICES: GoProDevice[] = [
  { name: "GoPro HERO12", ip: "10.5.5.9", model: "HERO12 Black", status: "offline" },
  { name: "GoPro HERO11", ip: "10.5.5.10", model: "HERO11 Black", status: "offline" },
];

export function GoProScreen({ navigate }: { navigate: (s: Screen) => void }) {
  const [devices, setDevices] = useState<GoProDevice[]>(DEMO_DEVICES);
  const [scanning, setScanning] = useState(false);
  const [connectedDevice, setConnectedDevice] = useState<GoProDevice | null>(null);

  const scanForDevices = () => {
    setScanning(true);
    setTimeout(() => {
      setDevices((prev) =>
        prev.map((d) => ({ ...d, status: d.ip === "10.5.5.9" ? "online" : "offline" }))
      );
      setScanning(false);
    }, 2000);
  };

  const connect = (device: GoProDevice) => {
    setDevices((prev) =>
      prev.map((d) => (d.ip === device.ip ? { ...d, status: "connecting" } : d))
    );
    setTimeout(() => {
      setDevices((prev) =>
        prev.map((d) =>
          d.ip === device.ip ? { ...d, status: "online" } : d
        )
      );
      setConnectedDevice(device);
    }, 1500);
  };

  const disconnect = () => {
    setConnectedDevice(null);
    setDevices((prev) =>
      prev.map((d) => ({ ...d, status: d.ip === connectedDevice?.ip ? "online" : d.status }))
    );
  };

  return (
    <div className="flex-1 flex overflow-hidden">
      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-white">GoPro 摄像机</h2>
            <p className="text-xs text-white/40 mt-0.5">通过WiFi连接GoPro进行远程拍摄</p>
          </div>
          <GlowBtn size="sm" variant="ghost" onClick={() => navigate("camera")}>返回拍照</GlowBtn>
        </div>

        <div className="flex gap-3">
          <GlowBtn size="sm" variant="primary" onClick={scanForDevices} disabled={scanning}>
            {scanning ? "扫描中..." : "扫描设备"}
          </GlowBtn>
          {connectedDevice && (
            <GlowBtn size="sm" variant="outline" onClick={disconnect}>断开连接</GlowBtn>
          )}
        </div>

        {connectedDevice && (
          <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
            <GlassCard className="p-4 border-emerald-500/30">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-emerald-500/20 flex items-center justify-center">
                  <span className="text-emerald-400 text-lg">G</span>
                </div>
                <div className="flex-1">
                  <div className="text-sm font-semibold text-white">{connectedDevice.name} (已连接)</div>
                  <div className="text-xs text-emerald-400/80">IP: {connectedDevice.ip} | {connectedDevice.model}</div>
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
          {devices.map((device) => (
            <GlassCard key={device.ip} className="p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`w-3 h-3 rounded-full ${
                  device.status === "online" ? "bg-emerald-400" :
                  device.status === "connecting" ? "bg-yellow-400 animate-pulse" :
                  "bg-white/20"
                }`} />
                <div>
                  <div className="text-sm text-white">{device.name}</div>
                  <div className="text-xs text-white/40">{device.model} - {device.ip}</div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className={`text-xs ${
                  device.status === "online" ? "text-emerald-400" :
                  device.status === "connecting" ? "text-yellow-400" :
                  "text-white/30"
                }`}>
                  {device.status === "online" ? "在线" :
                   device.status === "connecting" ? "连接中..." : "离线"}
                </span>
                <GlowBtn
                  size="sm"
                  variant={device.status === "online" ? "primary" : "outline"}
                  disabled={device.status !== "online" || !!connectedDevice}
                  onClick={() => connect(device)}
                >
                  连接
                </GlowBtn>
              </div>
            </GlassCard>
          ))}
        </div>
      </div>
    </div>
  );
}
