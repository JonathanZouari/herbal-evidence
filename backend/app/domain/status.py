# Mirror of public.request_status_transitions (tests assert they are equal). The DB trigger is the final guard.
TRANSITIONS: dict[str, set[str]] = {
    "submitted": {"researching", "withdrawn", "closed"},
    "researching": {"draft_ready", "research_failed", "withdrawn"},
    "research_failed": {"researching", "withdrawn", "closed"},
    "draft_ready": {"in_review", "withdrawn", "closed"},
    "in_review": {"awaiting_clarification", "published", "researching", "withdrawn", "closed"},
    "awaiting_clarification": {"in_review", "withdrawn", "closed"},
    "published": {"withdrawn"},
    "withdrawn": set(),
    "closed": set(),
}

# States from which staff may re-run research (the worker moves the request to `researching` on claim).
RERUNNABLE = {"research_failed", "in_review"}


def can_transition(src: str, dst: str) -> bool:
    return dst in TRANSITIONS.get(src, set())
