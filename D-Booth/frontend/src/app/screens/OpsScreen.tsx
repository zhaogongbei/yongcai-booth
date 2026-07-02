import {
  AlertTriangle,
  BarChart3,
  Camera,
  ChevronRight,
  CheckCircle2,
  ClipboardList,
  GalleryHorizontal,
  Image,
  Lock,
  Monitor,
  Printer,
  RefreshCw,
  Share2,
  Video,
  Wand2,
  Workflow,
} from "lucide-react";
import { GlassCard } from "../components/GlassCard";
import { GlowBtn } from "../components/GlowBtn";
import { NeonBadge } from "../components/NeonBadge";
import { StatusPill } from "../components/StatusPill";
import { apiTone, cameraTone, printerTone, useBoothHealth } from "../hooks/useBoothHealth";
import type { Screen } from "../types";

type OpsItem = {
  title: string;
  detail: string;
  target: Screen;
  icon: typeof Camera;
  accent: "purple" | "pink" | "blue" | "green";
};

type OpsGroup = {
  title: string;
  priority: "P0" | "P1" | "P2";
  items: OpsItem[];
};

const groups: OpsGroup[] = [
  {
    title: "现场开机检查",
    priority: "P0",
    items: [
      { title: "相机向导", detail: "检测相机、闪光灯、曝光与试拍结果", target: "camera-wizard", icon: Camera, accent: "purple" },
      { title: "打印校准", detail: "对齐、边距、裁切与出片前检查", target: "printer-calibration", icon: Printer, accent: "blue" },
      { title: "绿幕配置", detail: "背景替换、抠图参数与现场预览", target: "green-screen", icon: Wand2, accent: "green" },
      { title: "锁屏控制", detail: "现场防误触、PIN 与值守模式", target: "lock", icon: Lock, accent: "pink" },
    ],
  },
  {
    title: "活动工作流",
    priority: "P1",
    items: [
      { title: "调查配置", detail: "收集用户资料、问卷与隐私授权字段", target: "survey-config", icon: ClipboardList, accent: "blue" },
      { title: "触发器", detail: "遥控器、脚踏、传感器与自动化动作", target: "trigger-config", icon: Workflow, accent: "purple" },
      { title: "GoPro / 360", detail: "视频、慢动作、环拍与运动相机流程", target: "gopro", icon: Video, accent: "green" },
      { title: "展位管理", detail: "多展位状态、设备健康与活动编排", target: "booth-manager", icon: Monitor, accent: "pink" },
    ],
  },
  {
    title: "运营增强",
    priority: "P2",
    items: [
      { title: "模板编辑", detail: "版式、占位图、品牌元素与活动主题", target: "templates", icon: Image, accent: "purple" },
      { title: "分享链路", detail: "二维码、邮件、短信与上传渠道", target: "sharing", icon: Share2, accent: "blue" },
      { title: "相册导出", detail: "缩略图、筛选、收藏与交付资产", target: "gallery", icon: GalleryHorizontal, accent: "green" },
      { title: "运营统计", detail: "拍摄量、分享量、打印量与转化表现", target: "analytics", icon: BarChart3, accent: "pink" },
    ],
  },
];

export function OpsScreen({ navigate }: { navigate: (s: Screen) => void }) {
  const health = useBoothHealth();

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-6">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-5">
        <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <div className="mb-2 flex items-center gap-2">
              <NeonBadge color="purple">Booth Ops</NeonBadge>
              <NeonBadge color="green">现场运营</NeonBadge>
            </div>
            <h1 className="text-2xl font-semibold text-white md:text-3xl">运营控制台</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-white/55">
              将相机、打印、绿幕、触发器、问卷、分享和数据统计集中到一个现场操作入口。
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <GlowBtn variant="ghost" onClick={() => navigate("camera")}>
              <Camera size={16} />
              进入拍摄
            </GlowBtn>
            <GlowBtn variant="outline" onClick={() => navigate("print")}>
              <Printer size={16} />
              打印中心
            </GlowBtn>
            <GlowBtn variant="ghost" onClick={() => void health.refresh()} disabled={health.loading}>
              <RefreshCw size={16} className={health.loading ? "animate-spin" : ""} />
              刷新状态
            </GlowBtn>
          </div>
        </div>

        <GlassCard className="p-4">
          <div className="mb-4 flex flex-col gap-3 border-b border-white/5 pb-4 md:flex-row md:items-start md:justify-between">
            <div className="flex items-start gap-3">
              <div className={`rounded-xl border p-2 ${health.overall === "error" ? "border-red-500/25 bg-red-500/10 text-red-300" : health.overall === "warn" ? "border-yellow-500/25 bg-yellow-500/10 text-yellow-300" : "border-emerald-500/25 bg-emerald-500/10 text-emerald-300"}`}>
                {health.overall === "ok" ? <CheckCircle2 size={20} /> : <AlertTriangle size={20} />}
              </div>
              <div>
                <div className="text-sm font-semibold text-white">
                  {health.overall === "ok" ? "现场状态正常" : health.overall === "warn" ? "现场可运行，但需要注意" : "现场存在阻塞问题"}
                </div>
                <div className="mt-1 text-xs leading-5 text-white/45">
                  {health.issues.length > 0 ? health.issues.slice(0, 2).join("；") : "相机、打印、后端和队列均处于可运营状态"}
                </div>
              </div>
            </div>
            <StatusPill
              label={health.ready ? "可运营" : "需处理"}
              tone={health.overall}
            />
          </div>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
            <HealthCell
              label="后端服务"
              value={health.api.online ? health.api.status : "离线"}
              tone={apiTone(health.api)}
            />
            <HealthCell
              label="相机"
              value={health.camera.connected ? (health.camera.model || health.camera.controllerType || "已连接") : "未连接"}
              tone={cameraTone(health.camera)}
            />
            <HealthCell
              label="默认打印机"
              value={health.selectedPrinter?.name || "未检测到"}
              tone={printerTone(health.selectedPrinter)}
            />
            <HealthCell
              label="打印队列"
              value={`${health.queue.total} 个任务`}
              tone={health.queue.blocked > 0 ? "error" : health.queue.total > 0 ? "warn" : "ok"}
            />
          </div>
        </GlassCard>

        {groups.map((group) => (
          <section key={group.title} className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-white/80">{group.title}</h2>
              <NeonBadge color={group.priority === "P0" ? "pink" : group.priority === "P1" ? "blue" : "green"}>
                {group.priority}
              </NeonBadge>
            </div>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
              {group.items.map((item) => (
                <button
                  key={item.title}
                  type="button"
                  onClick={() => navigate(item.target)}
                  className="group text-left"
                  aria-label={`打开${item.title}`}
                >
                  <GlassCard className="h-full p-4 transition-colors hover:border-violet-400/25 hover:bg-white/[0.07]">
                    <div className="flex h-full flex-col gap-4">
                      <div className="flex items-start justify-between gap-3">
                        <div className={`rounded-xl border p-2 ${accentClasses[item.accent]}`}>
                          <item.icon size={20} />
                        </div>
                        <ChevronRight size={18} className="mt-1 text-white/25 transition-transform group-hover:translate-x-0.5 group-hover:text-white/60" />
                      </div>
                      <div>
                        <h3 className="text-base font-semibold text-white">{item.title}</h3>
                        <p className="mt-1 text-xs leading-5 text-white/50">{item.detail}</p>
                      </div>
                    </div>
                  </GlassCard>
                </button>
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}

function HealthCell({ label, value, tone }: { label: string; value: string; tone: "ok" | "warn" | "error" | "idle" }) {
  return (
    <div className="flex min-w-0 items-center justify-between gap-3 rounded-xl border border-white/5 bg-white/[0.03] px-3 py-2.5">
      <div className="min-w-0">
        <div className="text-[11px] text-white/35">{label}</div>
        <div className="truncate text-sm font-medium text-white/85">{value}</div>
      </div>
      <StatusPill label={tone === "ok" ? "正常" : tone === "warn" ? "注意" : tone === "error" ? "异常" : "空闲"} tone={tone} />
    </div>
  );
}

const accentClasses: Record<OpsItem["accent"], string> = {
  purple: "border-violet-500/25 bg-violet-500/10 text-violet-300",
  pink: "border-pink-500/25 bg-pink-500/10 text-pink-300",
  blue: "border-blue-500/25 bg-blue-500/10 text-blue-300",
  green: "border-emerald-500/25 bg-emerald-500/10 text-emerald-300",
};
