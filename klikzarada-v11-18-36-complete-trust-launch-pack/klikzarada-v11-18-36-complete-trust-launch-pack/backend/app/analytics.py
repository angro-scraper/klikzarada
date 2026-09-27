"""Privacy-preserving rules for the public page-view dashboard."""

from datetime import datetime

from sqlalchemy.orm import Session

from .models import SystemSetting


# Page-view analytics is intentionally limited to acquisition and public-entry
# screens. Authenticated workspaces have their own operational metrics.
PUBLIC_PAGEVIEW_PATHS = frozenset({
    "/",
    "/zadaci",
    "/registracija",
    "/prijava",
    "/oglasivac/prijava",
    "/oglasivac/registracija",
    "/pravila",
    "/pomoc",
})

ANALYTICS_POLICY_KEY = "analytics_pageview_policy"
ANALYTICS_POLICY_VERSION = "public_navigation_v2"
ANALYTICS_STARTED_AT_KEY = "analytics_pageviews_started_at"


def is_public_pageview_path(path: str) -> bool:
    return path in PUBLIC_PAGEVIEW_PATHS


def start_clean_pageview_measurement(
    db: Session,
    now: datetime | None = None,
    *,
    force: bool = False,
) -> datetime:
    """Activate the current measurement policy and return its UTC start."""
    now = now or datetime.utcnow()
    policy = db.query(SystemSetting).filter(SystemSetting.key == ANALYTICS_POLICY_KEY).first()
    started_at = db.query(SystemSetting).filter(SystemSetting.key == ANALYTICS_STARTED_AT_KEY).first()
    needs_new_series = force or not policy or policy.value != ANALYTICS_POLICY_VERSION or not started_at

    if needs_new_series:
        timestamp = now.replace(microsecond=0).isoformat() + "Z"
        if policy:
            policy.value = ANALYTICS_POLICY_VERSION
            policy.description = "Pravila za strogo merenje javnih navigacija u browseru."
        else:
            db.add(SystemSetting(
                key=ANALYTICS_POLICY_KEY,
                value=ANALYTICS_POLICY_VERSION,
                description="Pravila za strogo merenje javnih navigacija u browseru.",
            ))
        if started_at:
            started_at.value = timestamp
            started_at.description = "Početak čiste serije javnih navigacija u browseru."
        else:
            db.add(SystemSetting(
                key=ANALYTICS_STARTED_AT_KEY,
                value=timestamp,
                description="Početak čiste serije javnih navigacija u browseru.",
            ))
        return now.replace(microsecond=0)

    try:
        return datetime.fromisoformat(started_at.value.replace("Z", "+00:00")).replace(tzinfo=None)
    except (AttributeError, TypeError, ValueError):
        # A malformed legacy value must never make old, unscoped records visible.
        return start_clean_pageview_measurement(db, now, force=True)
