import React, { useState, Suspense, useEffect } from "react";
import {
  Camera, LayoutDashboard, Image, CalendarDays, GalleryHorizontal,
  Share2, BarChart3, Sparkles, Settings, HelpCircle, Printer,
  Monitor, Wrench, UserRound
} from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { Toaster } from "sonner";

import { SettingsProvider, useSettings } from "./stores/useSettings";
import { AuthProvider, useAuth } from "./stores/useAuth";
import { CaptureFlowProvider } from "./stores/useCaptureFlow";
import { BoothHealthProvider } from "./hooks/useBoothHealth";
import { initCsrfToken } from "../lib/api";

import { SplashScreen } from "./screens/SplashScreen";
const DashboardScreen = React.lazy(() => import("./screens/DashboardScreen").then(m => ({ default: m.DashboardScreen })));
const CameraScreen = React.lazy(() => import("./screens/CameraScreen").then(m => ({ default: m.CameraScreen })));
const BeautyScreen = React.lazy(() => import("./screens/BeautyScreen").then(m => ({ default: m.BeautyScreen })));
const TemplatesScreen = React.lazy(() => import("./screens/TemplatesScreen").then(m => ({ default: m.TemplatesScreen })));
const TemplateEditorScreen = React.lazy(() => import("./screens/TemplateEditorScreen").then(m => ({ default: m.TemplateEditorScreen })));
const PrintScreen = React.lazy(() => import("./screens/PrintScreen").then(m => ({ default: m.PrintScreen })));
const SharingScreen = React.lazy(() => import("./screens/SharingScreen").then(m => ({ default: m.SharingScreen })));
const EventsScreen = React.lazy(() => import("./screens/EventsScreen").then(m => ({ default: m.EventsScreen })));
const AIStudioScreen = React.lazy(() => import("./screens/AIStudioScreen").then(m => ({ default: m.AIStudioScreen })));
const AttractScreen = React.lazy(() => import("./screens/AttractScreen").then(m => ({ default: m.AttractScreen })));
const GalleryScreen = React.lazy(() => import("./screens/GalleryScreen").then(m => ({ default: m.GalleryScreen })));
const AnalyticsScreen = React.lazy(() => import("./screens/AnalyticsScreen").then(m => ({ default: m.AnalyticsScreen })));
const OpsScreen = React.lazy(() => import("./screens/OpsScreen").then(m => ({ default: m.OpsScreen })));
const SettingsScreen = React.lazy(() => import("./screens/SettingsScreen").then(m => ({ default: m.SettingsScreen })));
const SignatureScreen = React.lazy(() => import("./screens/SignatureScreen").then(m => ({ default: m.SignatureScreen })));
const SurveyScreen = React.lazy(() => import("./screens/SurveyScreen").then(m => ({ default: m.SurveyScreen })));
const DisclaimerScreen = React.lazy(() => import("./screens/DisclaimerScreen").then(m => ({ default: m.DisclaimerScreen })));
const SurveyConfigScreen = React.lazy(() => import("./screens/SurveyConfigScreen").then(m => ({ default: m.SurveyConfigScreen })));
const LockScreen = React.lazy(() => import("./screens/LockScreen").then(m => ({ default: m.LockScreen })));
const GreenScreenScreen = React.lazy(() => import("./screens/GreenScreenScreen").then(m => ({ default: m.GreenScreenScreen })));
const CameraWizardScreen = React.lazy(() => import("./screens/CameraWizardScreen").then(m => ({ default: m.CameraWizardScreen })));
const BoothManagerScreen = React.lazy(() => import("./screens/BoothManagerScreen").then(m => ({ default: m.default })));
const TriggerConfigScreen = React.lazy(() => import("./screens/TriggerConfigScreen").then(m => ({ default: m.TriggerConfigScreen })));
const GoProScreen = React.lazy(() => import("./screens/GoProScreen").then(m => ({ default: m.GoProScreen })));

import { TopBar } from "./components/TopBar";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { ActivationGate } from "./components/ActivationGate";

import { useBreakpoint } from "./components/ui/use-mobile";
import type { NavItem, Screen } from "./types";

// ─── Loading Skeleton ────────────────────────────────────────────────────────
function LoadingSkeleton() {
  return (
    <div className="flex-1 flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="w-12 h-12 rounded-2xl bg-white/5 animate-pulse" />
        <div className="w-40 h-3 rounded bg-white/5 animate-pulse" />
        <div className="w-28 h-3 rounded bg-white/5 animate-pulse" />
      </div>
    </div>
  );
}

// ─── Constants ────────────────────────────────────────────────────────────────
const NAV_ITEMS: NavItem[] = [
  { id: "dashboard", icon: LayoutDashboard, label: "主页" },
  { id: "camera", icon: Camera, label: "相机" },
  { id: "templates", icon: Image, label: "模板" },
  { id: "events", icon: CalendarDays, label: "活动" },
  { id: "gallery", icon: GalleryHorizontal, label: "相册" },
  { id: "sharing", icon: Share2, label: "分享" },
  { id: "analytics", icon: BarChart3, label: "统计" },
  { id: "ai-studio", icon: Sparkles, label: "AI工坊" },
  { id: "attract", icon: Monitor, label: "欢迎屏" },
  { id: "print", icon: Printer, label: "打印" },
  { id: "ops", icon: Wrench, label: "运营" },
  { id: "settings", icon: Settings, label: "设置" },
];

// Mobile bottom nav: only show top 5 + settings
const MOBILE_NAV_ITEMS: NavItem[] = [
  NAV_ITEMS[0], // 主页
  NAV_ITEMS[1], // 相机
  NAV_ITEMS[2], // 模板
  NAV_ITEMS[4], // 相册
  NAV_ITEMS[11], // 设置
];

// ─── Sidebar (Desktop/Tablet) ─────────────────────────────────────────────────
function SidebarUserBadge() {
  const { user } = useAuth();
  const label = user ? (user.full_name?.trim() || user.email) : "未登录";
  const initial = user ? label.charAt(0).toUpperCase() : null;
  return (
    <div
      className="w-8 h-8 rounded-full bg-gradient-to-br from-violet-500 to-pink-500 flex items-center justify-center text-xs font-bold text-white"
      title={label}
    >
      {initial ?? <UserRound size={14} className="text-white/80" />}
    </div>
  );
}

function Sidebar({ screen, navigate, width }: { screen: Screen; navigate: (s: Screen) => void; width: number }) {
  return (
    <div className="flex flex-col" style={{ width, background: "#080d1f", borderRight: "1px solid rgba(139,92,246,0.08)", flexShrink: 0 }} role="navigation" aria-label="主导航">
      {/* Logo */}
      <div className="flex items-center justify-center py-4 border-b border-white/5">
        <div className="w-9 h-9 rounded-xl flex items-center justify-center"
          style={{ background: "linear-gradient(135deg, #7c3aed, #8b5cf6)", boxShadow: "0 0 16px rgba(139,92,246,0.5)" }}>
          <Camera size={18} className="text-white" />
        </div>
      </div>

      {/* Nav items */}
      <div className="flex-1 flex flex-col items-center gap-1 py-3 overflow-y-auto">
        {NAV_ITEMS.map(item => {
          const active = screen === item.id;
          return (
            <motion.button key={item.id} onClick={() => navigate(item.id)}
              className="relative flex flex-col items-center gap-1 w-full px-1 py-2.5 cursor-pointer group"
              whileTap={{ scale: 0.92 }}
              aria-label={item.label}
              aria-current={active ? "page" : undefined}
            >
              {active && (
                <motion.div layoutId="nav-pill"
                  className="absolute inset-x-2 inset-y-1 rounded-xl"
                  style={{ background: "rgba(139,92,246,0.15)" }}
                  transition={{ type: "spring", stiffness: 500, damping: 40 }}
                />
              )}
              {active && <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-6 rounded-r-full bg-violet-500" />}
              <div className="relative">
                <item.icon size={19} className={`transition-colors ${active ? "text-violet-400" : "text-white/30 group-hover:text-white/60"}`} />
              </div>
              <span className={`relative text-[9px] font-medium leading-none transition-colors ${active ? "text-violet-400" : "text-white/25 group-hover:text-white/50"}`}>
                {item.label}
              </span>
            </motion.button>
          );
        })}
      </div>

      {/* Bottom */}
      <div className="pb-4 flex flex-col items-center gap-1 border-t border-white/5 pt-3">
        <button className="flex flex-col items-center gap-1 p-2 text-white/30 hover:text-white/60 transition-colors" aria-label="帮助">
          <HelpCircle size={18} />
          <span className="text-[9px]">帮助</span>
        </button>
        <SidebarUserBadge />
      </div>
    </div>
  );
}

// ─── Bottom Nav (Mobile) ──────────────────────────────────────────────────────
function BottomNav({ screen, navigate }: { screen: Screen; navigate: (s: Screen) => void }) {
  return (
    <nav className="flex items-center justify-around border-t"
      role="navigation" aria-label="移动端导航"
      style={{
        background: "#080d1f",
        borderColor: "rgba(139,92,246,0.08)",
        paddingBottom: "var(--safe-area-bottom, 0px)",
        flexShrink: 0,
      }}
    >
      {MOBILE_NAV_ITEMS.map(item => {
        const active = screen === item.id;
        return (
          <button key={item.id} onClick={() => navigate(item.id)}
            className="flex flex-col items-center gap-0.5 py-2 px-3 cursor-pointer"
            aria-label={item.label}
            aria-current={active ? "page" : undefined}
          >
            <item.icon size={20} className={active ? "text-violet-400" : "text-white/30"} />
            <span className={`text-[10px] font-medium leading-none ${active ? "text-violet-400" : "text-white/25"}`}>
              {item.label}
            </span>
          </button>
        );
      })}
    </nav>
  );
}

// ─── Main App ─────────────────────────────────────────────────────────────────
export default function App() {
  return (
    <SettingsProvider>
      <AuthProvider>
        <AppInner />
      </AuthProvider>
    </SettingsProvider>
  );
}

function AppInner() {
  const { settings } = useSettings();
  const [screen, setScreen] = useState<Screen>("splash");
  const [splashDone, setSplashDone] = useState(false);
  const { isMobile, isTablet } = useBreakpoint();

  // Initialize CSRF token on app startup
  useEffect(() => {
    initCsrfToken().catch((err) => {
      console.error('Failed to initialize CSRF token:', err);
    });
  }, []);

  const navigate = (s: Screen) => setScreen(s);

  // Sidebar width: tablet 56px, desktop 68px (ignored when mobile)
  const sidebarWidth = isTablet ? 56 : 68;

  const isFullscreen = screen === "attract";

  return (
    <ActivationGate>
      <BoothHealthProvider>
      <CaptureFlowProvider>
      <div>
      {screen === "splash" ? (
        <div className="w-full h-screen-fix" style={{ fontFamily: "'Inter', 'Noto Sans SC', system-ui, sans-serif", filter: `brightness(${settings.ui.brightness / 100})` }}>
          <SplashScreen onDone={() => { setSplashDone(true); setScreen("attract"); }} />
        </div>
      ) : (
        <div className="w-full h-screen-fix flex overflow-hidden"
          style={{
            fontFamily: "'Inter', 'Noto Sans SC', system-ui, sans-serif",
            background: "#050816",
            paddingTop: "var(--safe-area-top, 0px)",
            paddingBottom: "var(--safe-area-bottom, 0px)",
            paddingLeft: "var(--safe-area-left, 0px)",
            paddingRight: "var(--safe-area-right, 0px)",
            filter: `brightness(${settings.ui.brightness / 100})`,
          }}
        >
          {/* Sidebar (hidden on mobile, shown on tablet/desktop) */}
          {!isMobile && !isFullscreen && (
            <Sidebar screen={screen} navigate={navigate} width={sidebarWidth} />
          )}

          {/* Main area */}
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Top bar (not for attract) */}
            {screen !== "attract" && (
              <TopBar onSelectEvent={() => navigate("events")} />
            )}

            {/* Screen content */}
            <AnimatePresence mode="wait">
              <motion.div key={screen} className="flex-1 flex overflow-hidden"
                initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -8 }}
                transition={{ duration: 0.2, ease: "easeInOut" }}
              >
                <Suspense fallback={<LoadingSkeleton />}>
                  <ErrorBoundary>
                  {screen === "dashboard" && <DashboardScreen navigate={navigate} />}
                  {screen === "camera" && <CameraScreen navigate={navigate} />}
                  {screen === "beauty" && <BeautyScreen navigate={navigate} />}
                  {screen === "templates" && <TemplatesScreen navigate={navigate} />}
                  {screen === "template-editor" && <TemplateEditorScreen navigate={navigate} />}
                  {screen === "print" && <PrintScreen navigate={navigate} />}
                  {screen === "sharing" && <SharingScreen navigate={navigate} />}
                  {screen === "events" && <EventsScreen navigate={navigate} />}
                  {screen === "ai-studio" && <AIStudioScreen navigate={navigate} />}
                  {screen === "attract" && <AttractScreen navigate={navigate} />}
                  {screen === "gallery" && <GalleryScreen navigate={navigate} />}
                  {screen === "analytics" && <AnalyticsScreen navigate={navigate} />}
                  {screen === "ops" && <OpsScreen navigate={navigate} />}
                  {screen === "settings" && <SettingsScreen />}
                  {screen === "lock" && <LockScreen navigate={navigate} />}
                  {screen === "signature" && <SignatureScreen navigate={navigate} />}
                  {screen === "survey" && <SurveyScreen navigate={navigate} />}
                  {screen === "disclaimer" && <DisclaimerScreen navigate={navigate} />}
                  {screen === "survey-config" && <SurveyConfigScreen navigate={navigate} />}
                  {screen === "green-screen" && <GreenScreenScreen navigate={navigate} />}
                  {screen === "camera-wizard" && <CameraWizardScreen navigate={navigate} />}
                  {screen === "booth-manager" && <BoothManagerScreen navigate={navigate} />}
                  {screen === "trigger-config" && <TriggerConfigScreen navigate={navigate} />}
                  {screen === "gopro" && <GoProScreen navigate={navigate} />}
                  </ErrorBoundary>
                </Suspense>
              </motion.div>
            </AnimatePresence>

            {/* Bottom nav (mobile only) */}
            {isMobile && !isFullscreen && (
              <BottomNav screen={screen} navigate={navigate} />
            )}
          </div>
        </div>
      )}
      </div>
      <Toaster
        position="top-center"
        toastOptions={{
          style: { background: '#1a1a2e', color: '#fff', border: '1px solid rgba(139,92,246,0.2)' }
        }}
      />
      </CaptureFlowProvider>
      </BoothHealthProvider>
    </ActivationGate>
  );
}

