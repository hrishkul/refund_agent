INJECTION_PATTERNS = [
    "ignore previous",
    "override policy",
    "pretend you are",
    "as a dev mode",
    "ignore instructions",
    "disregard",
    "forget previous",
    "act as",
    "jailbreak",
    "bypass",
]


def check_injection(text: str) -> dict:
    normalized = text.lower()
    for pattern in INJECTION_PATTERNS:
        if pattern in normalized:
            return {"flagged": True, "pattern": pattern}
    return {"flagged": False, "pattern": None}

