import type { ElementType } from "react";

export type Screen =
  | "splash" | "dashboard" | "camera" | "beauty" | "templates"
  | "template-editor" | "print" | "sharing" | "events"
  | "ai-studio" | "attract" | "gallery" | "analytics" | "ops" | "settings"
  | "signature" | "survey" | "disclaimer" | "survey-config" | "lock" | "green-screen"
  | "camera-wizard" | "booth-manager" | "trigger-config" | "gopro";

export interface NavItem {
  id: Screen;
  icon: ElementType;
  label: string;
}
