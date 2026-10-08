# AgentPay Nexus UI modernization proposal

Status: approved by the user and implemented on 2026-10-08. All six frontend increments are complete. Audit findings below describe the pre-modernization baseline; implementation evidence and remaining limits are recorded in UI_REVIEW.md.

## Objective and boundaries

Present a polished commerce operations workspace suitable for a recruiter demonstration. Improve how people create purchase requests, understand quotes, manage merchant settings, review approvals, and inspect evidence.

Use the existing Next.js 16.3.3 App Router, React 19.2.8, TypeScript, Tailwind CSS 4, and Lucide icons. Current pages are client components selected within `app/page.tsx`; the buyer stays mounted to preserve drafts and operational pages refresh on entry. `lib/api.ts` owns typed FastAPI requests. The backend currently uses SQLite and a sequential Python coordinator; the durable architecture in `architecture_overview.md` is a future plan.

Keep request URLs, payloads, response contracts, polling cadence, payment callbacks, business rules, and existing access behavior intact. Presentation changes must not suggest durable orchestration, live streaming, recurring mandates, or payment settlement guarantees that are absent. Preserve the actual test checkout, receipt download, approval decisions, inventory updates, schema inspector, and scenario execution.

No new UI dependencies, animation library, chart library, font downloads, or backend endpoints are needed.

## Audit evidence

Playwright MCP opened the running app at http://localhost:3000 with the backend connected. All five sections were inspected at 1440 x 900 and 390 x 900, supplementing the earlier 360/768/1440 checks. Screenshots are stored locally in `.playwright-mcp/design-audit-{section}-{width}.png`.

| Finding | Evidence and impact | Priority |
| --- | --- | --- |
| Small typography dominates | Merchant screen includes 9–11 px badges/labels; buyer helpers and process labels use 10 px. Reading requires effort, especially on phones. | High |
| Weak visual hierarchy | Repeated page/component headings, similar white cards, oversized introductory panels, and many competing colored badges obscure the main task. | High |
| Inconsistent controls | Tailwind styles are repeated across components with different button padding, labels, radii, status treatments, and feedback behavior. | High |
| Long approval inbox | Current 11 approvals make the page approximately 9,640 px tall at 390 px. Policy settings remain far below the inbox despite a jump link. | High |
| Long audit list | All 100 loaded events appear in one list; the mobile page is approximately 10,461 px tall. Finding a specific event is cumbersome. | High |
| Contrast gaps | Theme calculations: slate-400 on white is 2.56:1; white on the blue-500 gradient endpoint is 3.68:1. These do not meet 4.5:1 for normal text. | High |
| Mobile catalog length | Product cards preserve usability but displaying all 12 creates a roughly 6,410 px page. Search and client pagination can reduce it. | Medium |
| Mobile navigation lacks product presence | Native section selection works, but a consistent branded menu and page context would better connect phone and desktop experiences. | Medium |
| Overstated copy remains | Strategy cards mention fixed margins/Autopay; scenario descriptions imply atomic financial rollback even while their introduction identifies scripted behavior. | High |
| Loading can resemble actual zero | Merchant cards render zero defaults before API data arrives. Use skeletons or unavailable placeholders, not apparent business measurements. | High |
| Draft/action context is unclear | Merchant edits have little persistent unsaved feedback; refresh reloads configuration. Buyer inputs can change during a running request, disconnecting the visible form from the submitted request. | Medium |
| Accessibility needs consistent behavior | Visual labels sometimes differ from accessible names; checkout close/copy controls are smaller than the intended 44 px targets; section changes do not intentionally move focus to the new heading. | High |

The audit found no document-level horizontal overflow, no browser warnings/errors, and no unnamed visible form/button controls in its basic scan. Existing focus outlines, skip link, native dialogs, mobile catalog cards, error alerts, and draft preservation are useful foundations. This is not a complete screen-reader or WCAG certification.

## Proposed design system

Direction: a restrained, premium operations product with a charcoal navigation rail, light surfaces, cobalt actions, generous headings, and compact evidence. Visual richness comes from composition, typography, and interaction rather than extra decoration.

| Token | Proposed value or rule |
| --- | --- |
| Canvas | `#F5F7FA` |
| Surface | `#FFFFFF`; secondary surface `#F8FAFC` |
| Navigation | `#101828`; light navigation text with measured contrast |
| Text | Primary `#0F172A`; secondary `#475569`; helper `#64748B` |
| Border | `#E2E8F0`; stronger field boundary where needed |
| Action | Solid cobalt `#2563EB`; hover `#1D4ED8`; white text |
| Semantic states | Emerald success, amber attention, rose failure; always pair color with words and icons |
| Typography | Existing Segoe UI/Arial; 30–32 px page titles, 18–20 px section titles, 14–16 px body/controls, 12 px metadata minimum |
| Numeric typography | Tabular numerals for amounts; monospace reserved for identifiers, hashes, and JSON |
| Spacing | 4/8/12/16/24/32/48 px scale |
| Radius | 10 px controls, 12–16 px cards/dialogs; consistent rather than oversized everywhere |
| Elevation | Subtle card shadow; larger shadow only for dialogs/overlays |
| Targets | At least 44 x 44 px for touch actions, including close/copy/stock controls |
| Motion | 120–180 ms opacity/color/transform transitions; only opacity/transform for entry motion; reduced-motion disables movement |

One primary action per task area. No perpetual pulsing, floating panels, confetti, or decorative shimmer. Loading skeletons use static placeholders when reduced motion is requested. White text never sits on the lighter blue endpoint of the existing gradient.

### Responsive shell

- At 1024 px and above: a 224 px navigation rail, compact top bar, clear page title and contextual status, and a bounded content area with 24–32 px gutters.
- Below 1024 px: a compact brand/menu bar and a native dialog containing the complete navigation list. Opening, Tab, Escape, and focus restoration must work.
- Navigation continues to use the existing section IDs and callbacks. The buyer remains mounted. No routing or history rewrite is part of this proposal.
- Main layouts stack according to actual content space. Avoid relying only on viewport width after introducing the rail.
- Phone gutters remain 16 px. Tables scroll within a labeled region; phone cards provide the same actions.

### Shared components

Add a small `components/ui/` layer for Button, IconButton, Panel, PageHeader, StatusBadge, Field, Toggle, MetricCard, StatePanel, Skeleton, Pagination, and dialog presentation/focus helpers. Keep domain actions in the current feature components. Existing CSS class names can remain compatibility wrappers during migration.

Components standardize variants, spacing, labels, focus rings, loading/disabled states, and status announcements. Avoid replacing native inputs, selects, details, or dialogs with custom widgets unless the existing behavior requires it. Payment overlay handoff remains specialized; a shared dialog helper must not change provider checkout behavior.

## Page-by-page implementation plan

| Page | Proposed structure and interactions | Features retained |
| --- | --- | --- |
| Buyer | Purchase composer with request first, compact scenario choices, clear budget and intent settings; larger review panel with quote total and policy decision as its primary content. Group quote lines, pricing breakdown, approval/checkout action, then expandable trace. Capture submitted request context for display; do not pretend intermediate stages are streaming. | All presets, growth strategy values, switches, budgets, workflow execution, quote data, decisions, provider checkout, trace details |
| Merchant | Six restrained metric cards with unavailable/loading states; pricing configuration with visible unsaved/saved feedback; consistent strategy switches; catalog search and pagination with desktop table/mobile cards. Confirm before discarding a dirty configuration through Refresh. Show backend facts without unsupported uplift or guaranteed-margin copy. | Metric values, strategy IDs, margin setting, configuration API, stock adjustment behavior, schema inspection |
| Policies & approvals | Desktop approval list and selected decision detail; mobile compact approval summaries with one expanded detail. Paginate fetched approvals and keep policy settings in a separate accessible panel. Preserve explicit per-purchase approval/rejection and busy locking; no bulk approval. Show all current policy controls and draft state. | Gate IDs/data, polling, decisions, resulting checkout order, limit/category/upsell settings, save behavior |
| Audit | Compact verification summary above an event explorer. Client-side search, actor/action filters derived from loaded events, 20 events per page, expandable evidence, readable local date formatting with original timestamp available, and 44 px copy controls. Label the dataset as the latest 100 loaded events, not the entire ledger. | Verification fields, integrity failure state, event ordering/content, full hashes, raw payload, copy fallback |
| Scenario lab | Three balanced scenario cards with concise objective and expected behavior. Clearly distinguish scripted expectation from the returned outcome. Show active request, result summary, and the existing expandable trace. Use motion only for transitions and loading feedback. | Existing scenario IDs/endpoints, disabled in-flight actions, real responses, approval callback, trace |
| Checkout/schema dialogs | Consistent dialog header/body/footer, accessible close action, contextual errors, responsive sizing, intentional focus and restoration. Keep the payment verification warning visible and specific. | Provider handoff, test-key/placeholder checks, verification callback, receipt download, modal cancellation restrictions |

Client pagination works on already fetched records; it does not change backend queries or imply server pagination. Searching resets the visible page. Approval selection follows a still-pending gate after polling; a removed gate clears stale details. Refreshed data must not invalidate a user's unrelated draft.

## Incremental implementation order and acceptance

1. **Foundation and shell.** Introduce tokens/shared controls and desktop/mobile shell. Check every section, page focus, navigation keyboard behavior, drawer focus containment, and responsive content width.
2. **Buyer workspace.** Apply composer/review hierarchy and common states. Check presets, budgets, switches, retained draft, request/error/loading rendering, quote/decision/trace sections, and checkout entry.
3. **Merchant operations.** Apply metric/configuration/catalog patterns. Check actual values, keyboard switches, draft feedback, refresh-discard handling, search/pagination, schema dialog, and unchanged stock request behavior.
4. **Approvals and policy.** Apply compact inbox/detail and policy panel. Check polling preserves edits and selections, paging, single gate busy state, approval/rejection payloads, and checkout data continuity.
5. **Audit explorer.** Apply compact rows/filters/pagination and status treatments. Check integrity success/failure/empty/unavailable states, bounded dataset labels, search reset, hash copy feedback, and JSON overflow.
6. **Scenario/dialog polish and final regression.** Unify scenario results and dialogs; remove obsolete style rules only after migration. Check reduced motion, long names/IDs/amounts, all loading/empty/error states, and representative payment overlay paths.

After each major increment: ESLint and `tsc --noEmit`; Playwright review of affected screens at 360, 390, 768, 1024, and 1440 px; console/network error inspection; document overflow checks; keyboard interactions/focus; labels and contrast; reduced motion. Add targeted regression checks when a changed interaction needs coverage, not tests that simply repeat markup.

Use Playwright response interception for deterministic UI state checks (slow/error/empty/failure responses) without changing backend behavior. Fixtures must be clearly test-only and match existing schemas. Do not repeatedly settle or approve real records merely to test styling. Final release build and all-screen browser regression follow the last increment. Build output must not disrupt the active preview; restart the dev preview if necessary.

Append changed behavior, evidence, test results, and remaining limits to `docs/UI_REVIEW.md` after each increment. Keep before/after screenshots in `docs/screenshots/` for representative buyer, operator, and mobile views.

## Approval and limits

Approval covers the visual direction, navigation shell, shared components, all page layouts, and the six-stage implementation order described above. The user approved implementation after reviewing this proposal. The six increments are now implemented and verified; this record retains the agreed scope.

The work improves frontend quality; backend financial safeguards and authentication/ownership gaps remain the separately documented architecture work. The current API cannot supply durable live workflow progress, historical revenue trends, fulfillment status, or recurring payment mandates. Do not draw charts or controls suggesting those capabilities.

Browser checks use Chromium viewport resizing. Physical devices, other engines, a full assistive-technology audit, and actual provider payment completion require separate evidence before claiming complete production readiness.
