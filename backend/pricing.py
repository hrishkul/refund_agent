import os
import time

import httpx


_cache = {"data": {}, "fetched_at": 0}


def fetch_pricing() -> dict:
    if time.time() - _cache["fetched_at"] > 86400:
        try:
            public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "")
            secret_key = os.getenv("LANGFUSE_SECRET_KEY", "")
            host = os.getenv("LANGFUSE_HOST", "http://langfuse:3000")

            if not public_key or not secret_key:
                return _cache["data"]

            res = httpx.get(
                f"{host}/api/public/models",
                auth=(public_key, secret_key),
                timeout=5,
            )
            res.raise_for_status()
            models = res.json().get("data", [])

            pricing = {}
            for model in models:
                name = model.get("modelName")
                prices = model.get("prices", {})
                if name and prices:
                    pricing[name] = {
                        "input": float(prices.get("input", {}).get("price", 0)),
                        "output": float(prices.get("output", {}).get("price", 0)),
                    }

            if pricing:
                _cache["data"] = pricing
                _cache["fetched_at"] = time.time()
        except Exception:
            pass
    return _cache["data"]


def calculate_cost(prompt_tokens: int, completion_tokens: int, model: str | None = None) -> float:
    model_name = model or os.getenv("MODEL_NAME", "gpt-4o")
    pricing = fetch_pricing()
    model_data = pricing.get(model_name)
    if model_data is None:
        model_data = pricing.get(next((key for key in pricing if key.lower() in model_name.lower()), None), {})
    cost = (prompt_tokens * model_data.get("input", 0)) + (completion_tokens * model_data.get("output", 0))
    return round(cost, 8)
