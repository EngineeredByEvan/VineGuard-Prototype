# VineGuard Web Dashboard

A Vite + React + TypeScript dashboard for monitoring vineyard sensor fleets. The app pairs Tailwind CSS with shadcn/ui primitives and renders telemetry with Recharts.

## Getting started

1. Copy `.env.example` to `.env` and configure the API location:

   ```bash
   cp .env.example .env
   ```

2. Install dependencies and launch the development server:

   ```bash
   npm install
   npm run dev
   ```

   The dashboard will be available at `http://localhost:5173`.

## Features

- Email/password authentication with automatic token refresh and a seeded demo fallback.
- React Router navigation for the organizational overview, site and node detail views, and the insights activity feed.
- Real-time telemetry via Server-Sent Events with an automatic polling fallback that streams mock data.
- Reusable UI elements such as metric cards, status pills, and insight badges based on shadcn/ui patterns.
- Command panel that issues `POST /commands` requests to adjust node publish intervals or stage OTA firmware URLs.

## Tech stack

- [Vite](https://vitejs.dev/) + React + TypeScript
- [Tailwind CSS](https://tailwindcss.com/) with [shadcn/ui](https://ui.shadcn.com/) component patterns
- [Recharts](https://recharts.org/) for time-series visualization
- [React Router](https://reactrouter.com/) for routing

The project ships with deterministic mock data so you can explore the dashboard without a running API. Configure `VITE_API_URL` to connect it to a live backend.
