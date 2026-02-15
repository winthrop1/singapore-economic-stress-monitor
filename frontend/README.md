# Singapore Stress Watch Frontend

React + Vite frontend for the Singapore Economic Stress Monitor portfolio page.

## Local development

```bash
npm install
npm run dev
```

## Environment variables

Copy `.env.example` to `.env` and set values:

- `VITE_API_BASE_URL` (optional): backend API base URL, e.g. `https://your-api-domain.com`
- `VITE_PORTFOLIO_URL` (optional): URL for the "Back to Portfolio" button
- `VITE_PROJECT_GITHUB_URL` (optional): fallback repository URL if data payload omits it
- `VITE_STATIC_DATA_BASE` (optional): static JSON base path

If no repository URL is supplied by API data or `VITE_PROJECT_GITHUB_URL`, GitHub CTA buttons are hidden.

If `VITE_API_BASE_URL` is set, the app fetches from backend API endpoints first:
- `/api/stress-monitor/latest`
- `/api/stress-monitor/history`
- `/api/stress-monitor/indicators`

If backend fetch fails (or no API URL is configured), the app falls back to static JSON in:
`public/projects/singapore-economic-stress-monitor/data/`

When `VITE_API_BASE_URL` is configured, frontend warms the backend via `/healthz` in the background and automatically refreshes queries after wake-up.

## Build and deploy

```bash
npm run build
```

Deploy to Vercel (recommended for free hosting). Ensure SPA rewrites are enabled (`vercel.json`).
