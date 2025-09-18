# VineGuard Dashboard

Single-page application for monitoring VineGuard telemetry, node health, and generated insights.

## Prerequisites

- Node.js 18+
- Yarn or npm (examples below use npm)

## Setup

```bash
cd dashboard
npm install
cp .env.example .env
# adjust VITE_API_BASE_URL if the backend runs elsewhere
```

## Development server

```bash
npm run dev
```

The app will prompt for the demo credentials from the backend seed script and then render
telemetry/insights once authenticated.

## Production build

```bash
npm run build
npm run preview  # optional smoke test of the bundled app
```

## Linting

```bash
npm run lint
```
