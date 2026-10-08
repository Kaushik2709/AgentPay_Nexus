# AgentPay Nexus frontend

Next.js workspace for buyer purchasing, merchant inventory/pricing, policy approvals, audit inspection, and scripted scenarios.

See [the project README](../README.md) for setup and demonstration, [the implementation specification](../docs/PROJECT_SPECIFICATION.md) for contracts and architecture, and [the audit](../docs/ARCHITECTURE_AUDIT.md) for current limitations.

From this directory, run `npm ci` and `npm run dev`. The API defaults to `http://127.0.0.1:8000/api`; optionally copy `.env.example` to `.env.local` and change `NEXT_PUBLIC_API_URL`. Payment secrets belong only on the backend.

Checks: `npm run lint`, `npx tsc --noEmit`, and `npm run build`. All passed in the 2026-10-09 architecture review.
