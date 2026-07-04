import { useState, createContext, useContext } from "react";

export interface AppSettings {
  // Attract/欢迎屏
  attract: {
    autoPlay: boolean;
    carouselInterval: string; // "5" | "10"
    transition: string; // "fade" | "slide"
    selectedTemplate: number;
    selectedColor: number;
  };
  // 设备
  device: {
    camera: boolean;
    printer: boolean;
    cloud: boolean;
  };
  // 界面
  ui: {
    language: string;
    brightness: number; // 0-100
  };
  // 水印设置
  watermark: {
    enabled: boolean;
    position: "top_left" | "top_center" | "top_right" | "center" | "bottom_left" | "bottom_center" | "bottom_right" | "tile";
    opacity: number; // 0-100
    scale: number; // 10-200
    watermarkUrl: string;
    tile: boolean;
  };
  // 打印设置
  print: {
    sharpenProfile: "none" | "low" | "medium" | "high";
    preferredPrinterName: string;
  };
  // 虚拟助手设置
  virtualAttendant: {
    enabled: boolean;
    language: "zh-CN" | "en-US";
    voice: "female" | "male";
    volume: number;
    timings: Record<string, {
      enabled: boolean;
      text: string;
    }>;
  };
  lockScreen: {
    pinLength: number;
    pin: string;
    title: string;
    subtitle: string;
    backgroundImage: string;
  };
}

const DEFAULT_SETTINGS: AppSettings = {
  attract: {
    autoPlay: true,
    carouselInterval: "5",
    transition: "fade",
    selectedTemplate: 0,
    selectedColor: 0,
  },
  device: {
    camera: true,
    printer: true,
    cloud: true,
  },
  ui: {
    language: "zh-CN",
    brightness: 80,
  },
  watermark: {
    enabled: false,
    position: "bottom_right",
    opacity: 50,
    scale: 20,
    watermarkUrl: "",
    tile: false,
  },
  print: {
    sharpenProfile: "medium",
    preferredPrinterName: "HP LaserJet Professional P1108",
  },
  virtualAttendant: {
    enabled: true,
    language: "zh-CN",
    voice: "female",
    volume: 0.8,
    timings: {},
  },
  lockScreen: {
    pinLength: 4,
    pin: "",
    title: "拍照亭已锁定",
    subtitle: "",
    backgroundImage: "",
  },
};

type SettingsUpdate = Partial<AppSettings>;

interface CurrentEvent {
  id: string;
  name: string;
  teamId: string;
}

interface SettingsContextType {
  settings: AppSettings;
  updateSettings: (update: SettingsUpdate) => void;
  currentEvent: CurrentEvent | null;
  setCurrentEvent: (event: CurrentEvent | null) => void;
}

const SettingsContext = createContext<SettingsContextType | null>(null);

function loadSettings(): AppSettings {
  try {
    const stored = localStorage.getItem("aibooth_settings");
    if (stored) {
      const parsed = JSON.parse(stored) as Partial<AppSettings>;
      return {
        ...DEFAULT_SETTINGS,
        ...parsed,
        attract: { ...DEFAULT_SETTINGS.attract, ...parsed.attract },
        device: { ...DEFAULT_SETTINGS.device, ...parsed.device },
        ui: { ...DEFAULT_SETTINGS.ui, ...parsed.ui },
        watermark: { ...DEFAULT_SETTINGS.watermark, ...parsed.watermark },
        print: { ...DEFAULT_SETTINGS.print, ...parsed.print },
        virtualAttendant: { ...DEFAULT_SETTINGS.virtualAttendant, ...parsed.virtualAttendant },
        lockScreen: { ...DEFAULT_SETTINGS.lockScreen, ...parsed.lockScreen },
      };
    }
  } catch {}
  return DEFAULT_SETTINGS;
}

function saveSettings(settings: AppSettings) {
  try {
    localStorage.setItem("aibooth_settings", JSON.stringify(settings));
  } catch {}
}

export function SettingsProvider({ children }: { children: React.ReactNode }) {
  const [settings, setSettings] = useState<AppSettings>(loadSettings);
  const [currentEvent, setCurrentEvent] = useState<CurrentEvent | null>(null);

  const updateSettings = (update: SettingsUpdate) => {
    setSettings(prev => {
      const next = { ...prev };
      if (update.attract) next.attract = { ...prev.attract, ...update.attract };
      if (update.device) next.device = { ...prev.device, ...update.device };
      if (update.ui) next.ui = { ...prev.ui, ...update.ui };
      if (update.watermark) next.watermark = { ...prev.watermark, ...update.watermark };
      if (update.print) next.print = { ...prev.print, ...update.print };
      if (update.virtualAttendant) next.virtualAttendant = { ...prev.virtualAttendant, ...update.virtualAttendant };
      if (update.lockScreen) next.lockScreen = { ...prev.lockScreen, ...update.lockScreen };
      saveSettings(next);
      return next;
    });
  };

  return (
    <SettingsContext.Provider value={{ settings, updateSettings, currentEvent, setCurrentEvent }}>
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings() {
  const ctx = useContext(SettingsContext);
  if (!ctx) throw new Error("useSettings must be used within SettingsProvider");
  return ctx;
}
