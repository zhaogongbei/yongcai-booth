from copy import deepcopy
from typing import Any, Optional


DEFAULT_PLAN_ID = "free"

PLANS: dict[str, dict[str, Any]] = {
    "free": {
        "id": "free",
        "name": "Free",
        "price": 0,
        "currency": "usd",
        "interval": "month",
        "features": [
            "1 event",
            "50 photos per event",
            "10 AI credits monthly",
        ],
        "limits": {
            "photos_per_event": 50,
            "ai_credits_monthly": 10,
            "max_events": 1,
        },
    },
    "pro": {
        "id": "pro",
        "name": "Pro",
        "price": 499,
        "currency": "usd",
        "interval": "month",
        "features": [
            "20 events",
            "500 photos per event",
            "200 AI credits monthly",
        ],
        "limits": {
            "photos_per_event": 500,
            "ai_credits_monthly": 200,
            "max_events": 20,
        },
    },
    "enterprise": {
        "id": "enterprise",
        "name": "Enterprise",
        "price": 1999,
        "currency": "usd",
        "interval": "month",
        "features": [
            "Unlimited events",
            "Unlimited photos per event",
            "2000 AI credits monthly",
        ],
        "limits": {
            "photos_per_event": None,
            "ai_credits_monthly": 2000,
            "max_events": None,
        },
    },
}

PLAN_ALIASES = {
    plan["name"].lower(): plan_id
    for plan_id, plan in PLANS.items()
}


def normalize_plan_id(plan_name: Optional[str]) -> str:
    key = (plan_name or DEFAULT_PLAN_ID).strip().lower()
    return key if key in PLANS else PLAN_ALIASES.get(key, DEFAULT_PLAN_ID)


def get_plan(plan_name: Optional[str]) -> dict[str, Any]:
    return deepcopy(PLANS[normalize_plan_id(plan_name)])


def list_plans() -> list[dict[str, Any]]:
    return [deepcopy(plan) for plan in PLANS.values()]
