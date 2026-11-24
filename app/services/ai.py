"""Groq integration with reusable HTTP connections and compact prompts."""
import json
import time
import httpx
from app.config import settings

_http_client: httpx.AsyncClient | None = None
PERFORMANCE = {
    "groq_requests": 0,
    "groq_failures": 0,
    "groq_latency_ms_total": 0.0,
    "prompt_tokens": 0,
    "completion_tokens": 0,
}

async def get_http_client():
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(45.0, connect=10.0),
            limits=httpx.Limits(max_connections=30, max_keepalive_connections=10),
        )
    return _http_client

async def close_http_client():
    global _http_client
    if _http_client and not _http_client.is_closed:
        await _http_client.aclose()
    _http_client = None

class AIService:
    def __init__(self):
        self.enabled = bool(settings.groq_api_key and settings.ai_provider.lower() == "groq")
        self.mode = "Groq LLM" if self.enabled else "Rules Fallback"

    async def _call(self, system, user):
        if not self.enabled:
            return None
        started = time.perf_counter()
        try:
            client = await get_http_client()
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                json={
                    "model": settings.model_name,
                    "temperature": 0.2,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
            )
            response.raise_for_status()
            data = response.json()
            usage = data.get("usage") or {}
            PERFORMANCE["groq_requests"] += 1
            PERFORMANCE["prompt_tokens"] += int(usage.get("prompt_tokens", 0) or 0)
            PERFORMANCE["completion_tokens"] += int(usage.get("completion_tokens", 0) or 0)
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)
        except Exception:
            PERFORMANCE["groq_failures"] += 1
            return None
        finally:
            PERFORMANCE["groq_latency_ms_total"] += (time.perf_counter() - started) * 1000

async def infer_with_groq(customer, behavior, signals, engagements, fallback):
    service = AIService()
    if not service.enabled:
        return fallback
    system = (
        "You are the reasoning component of a proactive digital engagement system. "
        "Analyze observed customer behavior conservatively. Never claim a life event, "
        "financial distress, intent, or vulnerability as a fact. Return JSON only with "
        "possible_need, confidence (0 to 1), reason, sensitivity (standard or high), "
        "and evidence (array of short strings). Base the answer only on supplied data."
    )
    # Bound history and remove irrelevant profile fields to reduce prompt tokens.
    compact_customer = {k: customer.get(k) for k in (
        "customer_id", "customer_segment", "monthly_income_inr", "preferred_channel",
        "app_usage_frequency", "marketing_opt_out", "approx_account_balance_inr"
    )}
    payload = {
        "customer": compact_customer,
        "behavior_analysis": behavior,
        "behavioral_signals": (signals or [])[:3],
        "recent_engagements": (engagements or [])[:5],
    }
    result = await service._call(system, json.dumps(payload, default=str, separators=(",", ":")))
    if not isinstance(result, dict):
        return fallback
    try:
        confidence = max(0.0, min(1.0, float(result.get("confidence", fallback["confidence"]))))
        sensitivity = str(result.get("sensitivity", fallback["sensitivity"])).lower()
        if sensitivity not in {"standard", "high"}:
            sensitivity = fallback["sensitivity"]
        evidence = result.get("evidence", fallback.get("evidence", []))
        if not isinstance(evidence, list):
            evidence = fallback.get("evidence", [])
        return {
            "possible_need": str(result.get("possible_need", fallback["possible_need"])),
            "confidence": confidence,
            "reason": str(result.get("reason", fallback["reason"])),
            "sensitivity": sensitivity,
            "evidence": [str(x) for x in evidence[:5]],
        }
    except Exception:
        return fallback

async def message_with_groq(customer, need, action, fallback):
    service = AIService()
    if not service.enabled:
        return fallback
    system = (
        "Generate one short, respectful customer communication. Do not mention inferred "
        "financial stress or any sensitive inference as fact. Do not give financial advice. "
        "Do not pressure the customer. If the action is human review, do not generate a "
        "promotional message. Return JSON with message and tone."
    )
    compact_customer = {k: customer.get(k) for k in ("customer_id", "customer_segment", "preferred_channel")}
    payload = {"customer": compact_customer, "inferred_need": need, "next_best_action": action}
    result = await service._call(system, json.dumps(payload, default=str, separators=(",", ":")))
    if isinstance(result, dict) and result.get("message"):
        return str(result["message"])
    return fallback
