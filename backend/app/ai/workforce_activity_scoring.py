from datetime import date, datetime

from app.ai.workforce_activity_schemas import WorkforceAnalysisConfiguration

PRIORITY_WEIGHTS = {"low": 1, "medium": 2, "high": 3, "critical": 4}
OPEN_STATUSES = {"todo", "in_progress"}


def priority_weight(priority: str) -> int:
    return PRIORITY_WEIGHTS.get(priority, 0)


def capped_score(value: float, target: float, maximum: float) -> float:
    if target <= 0:
        return 0.0
    return round(min(value / target, 1.0) * maximum, 2)


def calculate_workload_components(
    tasks: list[object],
    active_project_assignments: int,
    today: date,
    window_start: datetime,
    config: WorkforceAnalysisConfiguration,
) -> tuple[dict[str, int], dict[str, float]]:
    def is_in_window(value: datetime | None) -> bool:
        if value is None:
            return False
        comparison_start = (
            window_start.replace(tzinfo=None) if value.tzinfo is None else window_start
        )
        return value >= comparison_start

    open_tasks = [task for task in tasks if getattr(task, "status") in OPEN_STATUSES]
    completed_tasks = [
        task
        for task in tasks
        if getattr(task, "status") == "completed"
        and is_in_window(getattr(task, "updated_at", None))
    ]
    priority_total = sum(priority_weight(getattr(task, "priority")) for task in open_tasks)
    overdue = sum(
        1
        for task in open_tasks
        if getattr(task, "due_date", None) is not None and getattr(task, "due_date") < today
    )
    due_soon = sum(
        1
        for task in open_tasks
        if getattr(task, "due_date", None) is not None
        and today <= getattr(task, "due_date") <= date.fromordinal(today.toordinal() + config.due_soon_days)
    )
    internal_events = sum(
        int(is_in_window(getattr(task, "created_at", None)))
        + int(is_in_window(getattr(task, "updated_at", None)))
        for task in tasks
    )
    raw = {
        "assigned_open_tasks": len(open_tasks),
        "priority_weight_total": priority_total,
        "overdue_tasks": overdue,
        "due_soon_tasks": due_soon,
        "active_project_assignments": active_project_assignments,
        "completed_tasks_in_window": len(completed_tasks),
        "internal_task_events_in_window": internal_events,
    }
    scores = {
        "open_task_score": capped_score(priority_total, 12, config.open_task_weight),
        "due_date_pressure_score": capped_score(overdue * 2 + due_soon, 6, config.due_date_weight),
        "active_project_load_score": capped_score(active_project_assignments, 3, config.active_project_weight),
        "completion_relief_score": capped_score(len(completed_tasks), 3, config.completion_relief_weight),
        "internal_task_activity_score": capped_score(internal_events, 5, config.internal_activity_weight),
    }
    return raw, scores


def workload_score(scores: dict[str, float]) -> float:
    return round(max(0.0, min(100.0, scores["open_task_score"] + scores["due_date_pressure_score"] + scores["active_project_load_score"] - scores["completion_relief_score"])), 2)


def classify_workload(score: float, config: WorkforceAnalysisConfiguration) -> str:
    if score < config.underloaded_threshold:
        return "underloaded"
    if score >= config.overloaded_threshold:
        return "overloaded"
    return "balanced"


def external_activity_score(event_count: int, maximum: float) -> float:
    return capped_score(event_count, 5, maximum)
