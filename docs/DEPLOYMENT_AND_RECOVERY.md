# Deployment and recovery

Updated October 11, 2026. This is a single-merchant test-payment application. PostgreSQL support covers the commerce database; Better Auth still uses its separate SQLite database.

## Database upgrade

Preserve both environment files and back up commerce/auth databases. Stop the API and its maintenance tasks during schema changes. From `server/`, run:

```powershell
.\venv\Scripts\python.exe -m app.db.migrations
```

The repeatable additive migration adds canonical `orders.amount_paise`, `orders.settled_at`, a singleton commerce writer lock, and unique indexes for provider order IDs, policy owners, and reservation order/SKU pairs. It backfills paise with decimal half-up rounding and preserves legacy INR columns. Duplicate legacy business keys or invalid legacy order amounts require investigation; the migration never silently deletes their rows. Back up before retrying failed SQLite DDL, which can leave additive schema changes in place.

`settled_at` records first local capture verification, rather than pretending the provider's order creation timestamp is its capture time. Legacy paid rows without capture timing receive the migration's observation time, conservatively counting their spend for another 24 hours. Existing pending approvals lack the new complete policy snapshot and must be regenerated. New quotes expire in ten minutes; pre-existing quotes retain their persisted expiry.

New tables receive stock/quantity check constraints. Existing SQLite tables receive additive columns/indexes, not a destructive table rebuild; their old check constraints are not retrofitted. Conditional application updates enforce the tested inventory invariants.

### Optional PostgreSQL commerce database

Install the driver, provision an empty database, and set both URLs to the same database in your existing configuration:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements-postgres.txt
# Example only; use your own deployment credentials, never commit them.
$env:DATABASE_URL='postgresql+psycopg://USER:PASSWORD@127.0.0.1:5432/agentpay'
$env:SYNC_DATABASE_URL=$env:DATABASE_URL
.\venv\Scripts\python.exe -m app.db.migrations
.\venv\Scripts\python.exe -m app.db.seed
```

Provision/seed once before starting multiple API processes. Do not concurrently seed an empty database. Windows psycopg requires a selector event loop; the database module configures the standard Uvicorn CLI accordingly. Custom launchers must also select a compatible loop. Both connection factories use the same PostgreSQL schema and database; mismatched database targets fail startup.

SQLite-to-PostgreSQL data transfer is a separate operation: there is no automatic live data copy, dual write, or online cutover. For a populated deployment, export/import under downtime, convert long legacy approval reasons to their codes, preserve IDs and integer amounts, reset PostgreSQL integer sequences after importing explicit IDs, verify inventory/reservations/audit chain, and reconcile all unresolved provider orders before enabling checkout. The default test catalog contains public demo merchant signing keys; replace them and rotate application secrets for a hosted deployment.

The database writer mutex intentionally serializes commerce writes across processes. PostgreSQL acquires a row lock via `UPDATE commerce_lock`; SQLite acquires its database writer lock. Inventory still uses guarded `UPDATE ... WHERE stock_quantity >= quantity`, with a savepoint for all-or-nothing carts. This preserves correctness in measured tests but constrains throughput. Do not remove the mutex without replacing workflow-key, approval, spend, settlement, and audit serialization with tested finer locks.

## Payment state and recovery

| State | Meaning | Safe next step |
| --- | --- | --- |
| `CREATING` | Reservation and provider receipt committed before submission; process might have crashed | Look up provider order by receipt; never resubmit creation |
| `RECONCILIATION_REQUIRED` | Timeout, cancellation, or malformed response leaves outcome unknown | Same receipt lookup; retain inventory and spending capacity |
| `CREATED` | Validated provider order ID and checkout persisted | Resume owned checkout before quote expiry; verify capture |
| `EXPIRED` | Entire stock hold released after expiry | Reconcile provider captures; request a fresh purchase for unpaid checkout |
| `PAID` | Captured payment verified; complete expected stock reservation consumed | Fulfillment can proceed within prototype scope |
| `PAID_REQUIRES_REVIEW` | Capture verified but expected reservation is missing or released | Operator review; never allocate stock or promise fulfillment automatically |

The API's maintenance task runs a sweep and waits 60 seconds before the next. It scans unresolved/known unpaid orders, performs provider calls outside database transactions, then releases expired known-order holds. Sweep duration grows with backlog; this is not a durable job queue or a fixed 60-second recovery SLA.

For unknown creation outcomes, the provider search must return exactly one order with the persisted receipt, quote ID note, integer amount, and INR currency. Zero, multiple, or conflicting matches leave the attempt uncertain. Discovery attaches the existing provider order, then known-order payment lookup can settle verified capture. No receipt is treated as a provider idempotency guarantee. Repeated sweeps and checkout/webhook races use the same settlement transaction.

If provider lookup fails, expired known-order stock can still be released; any later capture enters review instead of overselling. Unknown creation attempts retain their stock and spend capacity indefinitely until reconciled. If there is no provider match, operators must establish provider outcome from independent provider records before releasing the hold; an automatic cancellation/refund tool is not implemented.

Failed workflow responses remain persisted under their original idempotency keys after order recovery. Use authenticated order history to resume the recovered checkout; reusing the workflow key does not start another workflow. Missing idempotency keys identify separate requests. `RUNNING` workflows interrupted before order creation have no automatic workflow resume.

## Verification boundaries

Checkout verification first checks owned local order and HMAC, then fetches provider payment status. Webhooks verify HMAC over the raw body before passing entities to settlement. Maintenance uses authenticated provider lookups. Only these trusted entry points may provide payment entities to the settlement service; its injectable entity argument supports internal reconciliation and tests, not public client assertions.

Settlement requires matching payment/order ID, integer paise, INR currency, and `captured` status. Payment ID uniqueness, order state, and the writer lock prevent repeated inventory/audit effects. A second different captured payment for an already-paid order is rejected and needs operator investigation; automated refunds are outside scope. Approval authorizes checkout, never payment. Existing soft transaction-cap, daily-spend, and upsell exceptions can be approved under unchanged policy inputs and observed spend; category and signature failures cannot.

## Hosting requirements and limits

- Keep the backend private behind the authenticated Next.js proxy or equivalent trusted boundary. Use HTTPS, independent strong auth secrets, secure cookies, and immutable user-ID role allowlists.
- Configure only Razorpay test credentials and a separate test webhook secret. Live keys do not create an operational provider adapter. Do not run real payments with this prototype.
- Run a reachable HTTPS webhook endpoint in a sandbox deployment; configure capture behavior in Razorpay test mode. Actual provider delivery, retry timing, receipt lookup behavior, and secret rotation require separate sandbox verification.
- Back up both databases, monitor `CREATING`, `RECONCILIATION_REQUIRED`, `PAID_REQUIRES_REVIEW`, maintenance errors, and stale holds. Protect merchant signing keys and restrict direct database writes.
- Retain SQLite for local use on a persistent local disk. A single auth SQLite file, in-process maintenance, and global commerce serialization need further work before multi-host deployment.
- Pricing calculations and financial comparisons use integer paise, with Decimal for percentage calculations. Existing catalog/policy/order INR floats and API fields remain compatibility projections; migrating every legacy money column is deferred. Orders, quotes, and payment events persist canonical paise amounts for financial effects.

Primary references: [PostgreSQL explicit locks](https://www.postgresql.org/docs/17/explicit-locking.html), [SQLAlchemy psycopg sync/async dialect](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#module-sqlalchemy.dialects.postgresql.psycopg), [Razorpay receipt lookup](https://github.com/razorpay/razorpay-node/blob/master/documents/order.md), and [Razorpay duplicate webhook guidance](https://github.com/razorpay/markdown-docs/blob/master/webhooks/best-practices.md).
