/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_PORTFOLIO_URL?: string;
  readonly VITE_PROJECT_GITHUB_URL?: string;
  readonly VITE_STATIC_DATA_BASE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
