# Screwtape.ai for LangGraph

A judge for your agents that sits outside your agent stack. Screwtape isn't tied to any agent framework or AI model provider, so its verdicts never grade their own work. Every verdict comes with a signed receipt you can verify yourself, which gives you a record you can trust when it matters.

False-consensus check and pass/fail/retry verdicts for LangGraph agents. This example adds a **judge step** that routes on the verdict (pass → accept, retry → redo with the judge's reasons, fail → stop) and, where several answers exist, a **consensus step** that flags agreement too thin to trust.

## What it does

1. Your LangGraph agent drafts an answer from the evidence you give it.
2. The draft goes to `POST https://screwtape.ai/v1/judge` with the task, the evidence and the criteria.
3. The code routes on `verdict`. It prints `score`, `request_id` and the receipt id, so every decision is traceable.

## Files

- `graph.py`: `workers → consensus → judge`, with `add_conditional_edges("judge", route, ["accept", "workers", "reject"])`
- `screwtape.py`, `get_free_key.py`, `requirements.txt`
- `.env.example`, `.gitignore`, `LICENSE` (MIT)

## Setup and run

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export SCREWTAPE_API_KEY=...   # or use .env.example
python graph.py   # workers are stubs, so no LLM key is needed
```

## Routing

| Verdict | What the example does |
|---|---|
| `pass` | Return or accept the output |
| `retry` | Send the judge's `reasons` back to the worker and try again, up to a fixed cap |
| `fail` | Stop. Don't spend more calls on an answer the judge says is wrong |

The judge returns `verdict`, `score` (0 to 1), `reasons`, `engine` (`llm`, `deterministic` or `demo`), `request_id`, `retention` and, when signing is on, `receipt`. Consensus returns `consensus_answer`, `agreement_score`, `false_consensus_risk` (`low`, `medium` or `high`), `reasons`, `clusters`, `engine`, `request_id`, `retention` and `receipt`. The fields come from https://screwtape.ai/openapi.json.

## Signed verdict receipts

When receipt signing is on, every `/v1/judge` and `/v1/consensus` response also carries a `receipt` object. The fields are `receipt_id`, `issued_at`, `endpoint`, `request_sha256` (SHA-256 of the normalized request), `verdict`, `score`, `payment`, `alg` (`Ed25519`), `kid` and `signature`. For consensus, `verdict` is `false_consensus_risk` and `score` is `agreement_score`. `payment` shows the key prefix, never the key.

- Public keys: https://screwtape.ai/.well-known/screwtape-receipt-keys.json (JWKS-style Ed25519)
- Verify: `POST https://screwtape.ai/v1/receipts/verify` with the raw `receipt` object as the request body, exactly as returned (not wrapped in `{"receipt": ...}`). The response is `{"valid": true}` or `{"valid": false}`. No key is needed and the receipt isn't stored.

```python
from screwtape import judge, verify_receipt

v = judge("State the crew size.", "The crew size was 4.", evidence=["The crew size was 4."])
if "receipt" in v:
    print(v["receipt"]["receipt_id"], verify_receipt(v["receipt"]))
```

Store the receipt next to the output it approved, so a reviewer can later check which request was judged, the verdict it got, and when.

## Get a free key (10 calls per UTC day)

- **In a browser:** https://screwtape.ai/signup/ (email and name are optional, no card). To try judge and consensus with no key first, use https://screwtape.ai/try/ (3 calls per token, about 30 minutes).
- **From code or an agent:** `POST https://screwtape.ai/v1/signup` with a proof of work. The SHA-256 of `screwtape-signup-v1:<UTC YYYY-MM-DD>:<nonce>` must start with 12 zero bits, and the nonce must match `^[A-Za-z0-9_-]{8,64}$`. `python get_free_key.py --name my-agent` does this for you (`--dry-run` only finds the nonce).
- The key is shown **once**. Screwtape stores only its SHA-256 hash. Limits are 5 keys per IP per hour and 5 per UTC day.
- Copy `.env.example` to `.env` (git-ignored) or export `SCREWTAPE_API_KEY`. The code reads the key from the environment and never embeds it.

## Plans

- **Free:** 10 calls per UTC day with a free key.
- **Sandbox Evaluation Pack:** $100 for 2,000 checks. See https://screwtape.ai/pricing/.
- **Enterprise pilot:** email support@screwtape.ai.

A call without a key gets HTTP 402 Payment Required. This example catches it and tells you to set `SCREWTAPE_API_KEY`.

## Compatibility notes

- Replace `draft()` with your model call, and pass `state["feedback"]` (the judge's reasons) into the prompt on a retry.
- `MAX_ATTEMPTS` bounds the loop, so you get a clean `rejected` status instead of hitting the recursion limit.
- Without consensus, wire `worker → judge` directly. See https://screwtape.ai/blog/langgraph-validation-node/.
- Checked with langgraph 1.2.16. Stub runs gave retry, retry, pass → `accepted`, and fail → `rejected` after 1 attempt. A live keyless run printed the 402 hint.

## Links

- Screwtape.ai: https://screwtape.ai/
- API reference: https://screwtape.ai/docs/ · OpenAPI: https://screwtape.ai/openapi.json · For agents: https://screwtape.ai/llms.txt
- MCP server: https://screwtape.ai/mcp (MCP Registry name `ai.screwtape/screwtape`)
- Pricing: https://screwtape.ai/pricing/ · Free key: https://screwtape.ai/signup/
- Source for this example: https://github.com/screwtapeai/screwtape-langgraph
- Issues: https://github.com/screwtapeai/screwtape-langgraph/issues

## License

MIT. See [LICENSE](LICENSE). Copyright (c) 2026 Screwtape.ai.

---
Screwtape.ai is an agent validation API, not the arXiv paper that is also named Screwtape. This example was checked against the live API on 2026-10-21.
