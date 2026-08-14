from datetime import UTC, date, datetime, timedelta

from app.ai.workforce_activity_repository import WorkforceActivityRepository
from app.ai.workforce_activity_scoring import (
    calculate_workload_components,
    classify_workload,
    external_activity_score,
    workload_score,
)
from app.ai.workforce_activity_schemas import (
    EmployeeIdentityDTO,
    EmployeeWorkforceAnalysisDTO,
    UnattributedExternalActivityDTO,
    WorkforceAnalysisConfiguration,
    WorkforceAnalysisResultDTO,
    WorkforceComponentScoresDTO,
    WorkforceRawCountsDTO,
)
from app.config.settings import settings
from app.integrations.github_service import GitHubService
from app.integrations.jira_service import JiraService


class WorkforceActivityService:
    def __init__(
        self,
        repository: WorkforceActivityRepository,
        jira_service: JiraService | None = None,
        github_service: GitHubService | None = None,
        configuration: WorkforceAnalysisConfiguration | None = None,
    ):
        self.repository = repository
        self.jira_service = jira_service
        self.github_service = github_service
        self.configuration = configuration or self._configuration_from_settings()

    def analyze(self, now: datetime | None = None) -> WorkforceAnalysisResultDTO:
        now = now or datetime.now(UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        window_start = now - timedelta(days=self.configuration.window_days)
        workload_inputs = self.repository.get_employee_workload_inputs()
        external, jira_events, github_events = self._get_unattributed_external_activity(
            window_start, workload_inputs
        )
        employee_results = []
        for workload_input in workload_inputs:
            raw, scores = calculate_workload_components(
                workload_input.tasks,
                workload_input.active_project_assignments,
                now.date(),
                window_start,
                self.configuration,
            )
            raw["jira_activity_events"] = jira_events.get(workload_input.employee.id, 0)
            raw["github_activity_events"] = github_events.get(workload_input.employee.id, 0)
            scores["jira_activity_score"] = external_activity_score(raw["jira_activity_events"], self.configuration.jira_activity_weight)
            scores["github_activity_score"] = external_activity_score(raw["github_activity_events"], self.configuration.github_activity_weight)
            score = workload_score(scores)
            factors = self._factors(raw, score)
            employee_results.append(
                EmployeeWorkforceAnalysisDTO(
                    employee=EmployeeIdentityDTO(
                        id=workload_input.employee.id,
                        employee_code=workload_input.employee.employee_code,
                        first_name=workload_input.employee.first_name,
                        last_name=workload_input.employee.last_name,
                        designation=workload_input.employee.designation,
                    ),
                    workload_score=score,
                    activity_score=round(min(100.0, scores["internal_task_activity_score"] + scores["jira_activity_score"] + scores["github_activity_score"]), 2),
                    classification=classify_workload(score, self.configuration),
                    component_scores=WorkforceComponentScoresDTO(**scores),
                    raw_counts=WorkforceRawCountsDTO(**raw),
                    factors=factors,
                )
            )
        return WorkforceAnalysisResultDTO(
            generated_at=now,
            analysis_start_date=window_start.date(),
            configuration=self.configuration,
            employees=employee_results,
            unattributed_external_activity=external,
        )

    def _get_unattributed_external_activity(
        self, window_start: datetime, workload_inputs: list[object]
    ) -> tuple[UnattributedExternalActivityDTO, dict[object, int], dict[object, int]]:
        jira_issues = 0
        github_commits = github_prs = github_reviews = 0
        attributed_jira: dict[object, int] = {}
        attributed_github: dict[object, int] = {}
        unavailable: list[str] = []
        factors = ["Unmapped external activity remains aggregate-only and is not attributed to employees."]
        jira_mapping = {account_id: item.employee.id for item in workload_inputs for account_id in item.jira_account_ids}
        github_mapping = {user_id: item.employee.id for item in workload_inputs for user_id in item.github_user_ids}
        if self.jira_service is not None:
            try:
                jql = f'updated >= "{window_start.date().isoformat()}" ORDER BY updated DESC'
                issues = self.jira_service.search_issues(
                    jql, max_results=self.configuration.external_max_results, max_pages=1
                )
                for issue in issues:
                    employee_id = jira_mapping.get(issue.assignee_account_id)
                    if employee_id is None:
                        jira_issues += 1
                    else:
                        attributed_jira[employee_id] = attributed_jira.get(employee_id, 0) + 1
            except Exception:
                unavailable.append("jira")
        if self.github_service is not None:
            try:
                repositories = self.github_service.get_repositories(
                    max_results=1, max_pages=1
                )
                if repositories:
                    repository = repositories[0]
                    commits = self.github_service.get_commits(
                        repository.owner_login, repository.name, since=window_start,
                        max_results=self.configuration.external_max_results, max_pages=1
                    )
                    for commit in commits:
                        employee_id = github_mapping.get(str(commit.author_id)) if commit.author_id is not None else None
                        if employee_id is None:
                            github_commits += 1
                        else:
                            attributed_github[employee_id] = attributed_github.get(employee_id, 0) + 1
                    pull_requests = self.github_service.get_pull_requests(
                        repository.owner_login, repository.name,
                        max_results=self.configuration.external_max_results, max_pages=1
                    )
                    for pull_request in pull_requests:
                        employee_id = github_mapping.get(str(pull_request.author_id)) if pull_request.author_id is not None else None
                        if employee_id is None:
                            github_prs += 1
                        else:
                            attributed_github[employee_id] = attributed_github.get(employee_id, 0) + 1
                    if pull_requests:
                        reviews = self.github_service.get_pull_request_reviews(
                            repository.owner_login, repository.name, pull_requests[0].number,
                            max_results=self.configuration.external_max_results, max_pages=1
                        )
                        for review in reviews:
                            employee_id = github_mapping.get(str(review.reviewer_id)) if review.reviewer_id is not None else None
                            if employee_id is None:
                                github_reviews += 1
                            else:
                                attributed_github[employee_id] = attributed_github.get(employee_id, 0) + 1
            except Exception:
                unavailable.append("github")
        external = UnattributedExternalActivityDTO(
            jira_issue_count=jira_issues,
            jira_activity_score=external_activity_score(jira_issues, self.configuration.jira_activity_weight),
            github_commit_count=github_commits,
            github_pull_request_count=github_prs,
            github_review_count=github_reviews,
            github_activity_score=external_activity_score(github_commits + github_prs + github_reviews, self.configuration.github_activity_weight),
            unavailable_sources=unavailable,
            factors=factors,
        )
        return external, attributed_jira, attributed_github

    @staticmethod
    def _factors(raw: dict[str, int], score: float) -> list[str]:
        factors = [f"Workload score is {score} from priority-weighted task, due-date, project, and completion inputs."]
        if raw["overdue_tasks"]:
            factors.append(f"{raw['overdue_tasks']} overdue open task(s) increase due-date pressure.")
        if raw["due_soon_tasks"]:
            factors.append(f"{raw['due_soon_tasks']} open task(s) are due soon.")
        if raw["completed_tasks_in_window"]:
            factors.append(f"{raw['completed_tasks_in_window']} recently completed task(s) reduce workload.")
        if raw["jira_activity_events"]:
            factors.append(f"{raw['jira_activity_events']} Jira event(s) were attributed through an active exact account-ID mapping.")
        if raw["github_activity_events"]:
            factors.append(f"{raw['github_activity_events']} GitHub event(s) were attributed through an active exact user-ID mapping.")
        return factors

    @staticmethod
    def _configuration_from_settings() -> WorkforceAnalysisConfiguration:
        return WorkforceAnalysisConfiguration(
            window_days=settings.workforce_analysis_window_days,
            due_soon_days=settings.workforce_due_soon_days,
            open_task_weight=settings.workforce_open_task_weight,
            due_date_weight=settings.workforce_due_date_weight,
            active_project_weight=settings.workforce_active_project_weight,
            completion_relief_weight=settings.workforce_completion_relief_weight,
            internal_activity_weight=settings.workforce_internal_activity_weight,
            jira_activity_weight=settings.workforce_jira_activity_weight,
            github_activity_weight=settings.workforce_github_activity_weight,
            underloaded_threshold=settings.workforce_underloaded_threshold,
            overloaded_threshold=settings.workforce_overloaded_threshold,
            external_max_results=settings.workforce_external_max_results,
        )
