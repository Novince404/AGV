from __future__ import annotations

from app.models.platform_bug_feedback import PlatformBugFeedback


platform_bug_feedback_items: list[PlatformBugFeedback] = []


def list_platform_bug_feedback() -> list[PlatformBugFeedback]:
    return platform_bug_feedback_items


def get_platform_bug_feedback_by_id(feedback_id: int) -> PlatformBugFeedback | None:
    normalized_id = int(feedback_id or 0)
    return next((item for item in platform_bug_feedback_items if int(item.id) == normalized_id), None)


def get_next_platform_bug_feedback_id() -> int:
    return max((int(item.id) for item in platform_bug_feedback_items), default=0) + 1


def upsert_platform_bug_feedback(item: PlatformBugFeedback) -> PlatformBugFeedback:
    existing = get_platform_bug_feedback_by_id(item.id)
    if existing is None:
        platform_bug_feedback_items.append(item)
        return item
    platform_bug_feedback_items[platform_bug_feedback_items.index(existing)] = item
    return item
