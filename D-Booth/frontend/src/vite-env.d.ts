/// <reference types="vite/client" />

declare module "gif.js.optimized";

declare module "*.css";

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
  readonly VITE_APP_VERSION?: string;
  readonly VITE_WEB_VITALS_ENDPOINT?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
