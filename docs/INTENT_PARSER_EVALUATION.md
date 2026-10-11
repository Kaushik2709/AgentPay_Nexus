# Intent parser boundary and optional model evaluation

The active parser uses deterministic English/INR rules and catalog selection. Pricing strategies, financial authorization, ownership, approval, stock changes, and capture verification are deterministic. The sequential components named "agents" do not make the runtime a general autonomous AI system. No LLM was invoked or added to checkout in this work.

`server/benchmarks/intent_cases.json` freezes six catalog products and twelve cases: ordinary selection, full carts, exclusions, unsupported products, instruction injection, quantity limits, budgets, specifications, exact SKUs, foreign currency, conflicts, and multiple budget expressions. The current parser passed all twelve cases; see [the recorded baseline](benchmarks/intent-baseline.json). This small dataset supplements the broader parser unit tests and does not measure general language understanding.

From `server/`:

```powershell
.\venv\Scripts\python.exe -m benchmarks.intent_regression
# Optional later comparison with offline model proposals:
.\venv\Scripts\python.exe -m benchmarks.intent_regression --proposals proposals.json
```

Optional proposals must be a JSON object mapping each case ID to `{ "selected_skus": [...], "budget_paise": 2500000, "action": "PROPOSE" }`, with action `PROPOSE`, `CLARIFY`, or `UNAVAILABLE`. The tool compares exact outputs against both expected values and deterministic results. Missing/mismatched proposals are reported; there is no model provider call, credential handling, or commerce write. Actual LLM comparison remains unperformed because no model output was supplied.

If an LLM parser is later introduced, place it before catalog and policy validation as a suggestion source. Keep ambiguity/quantity/specification checks; independently bind candidates to the server catalog and the minimum authorized budget. Persist the validated quote and rerun the existing deterministic checks. A model's `PROPOSE` action grants no financial authority. Record model/version, prompt, outputs, cost, latency, and regression failures separately; do not deploy it on the strength of these twelve cases alone.
