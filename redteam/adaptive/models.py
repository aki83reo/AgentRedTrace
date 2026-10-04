from pydantic import BaseModel

from redteam.models.attack import AttackEvaluation, ToolExecution
from redteam.planner.models import PathDecision


class ComponentTrace(BaseModel):
    sequence: int
    component: str
    component_type: str
    reached: bool
    executed: bool
    status: str
    reason: str | None = None


class PathAnalysis(BaseModel):
    attempted_path: list[str]
    reachable_components: list[str]
    successful_components: list[str]
    blocked_components: list[str]
    failed_components: list[str]
    stopping_component: str | None
    stopping_reason: str | None
    untested_tools: list[str]
    component_traces: list[ComponentTrace]


class PathCoverage(BaseModel):
    known_tools: list[str]
    reached_tools: list[str]
    successful_tools: list[str]
    blocked_tools: list[str]
    failed_tools: list[str]
    untested_tools: list[str]
    attempted_paths: list[list[str]]
    unique_paths_attempted: int
    unexplored_paths: list[list[str]]


class PlannedEvaluationCase(BaseModel):
    attack_id: str
    root_attack_id: str
    parent_attack_id: str
    planned_path: list[str]
    generated_instruction: str
    generation_type: str


class PathAdherence(BaseModel):
    planned_path: list[str]
    actual_path: list[str]
    status: str
    matched_steps: int
    planned_steps: int
    reason: str


class AdaptiveRunSummary(BaseModel):
    attempts_executed: int
    root_attack_success: bool | None
    successful_attempt_id: str | None
    paths_observed: list[list[str]]
    planner_paths_selected: list[list[str]]
    stop_reason: str


class AdaptiveAttempt(BaseModel):
    attack_id: str
    root_attack_id: str = ""
    parent_attack_id: str | None
    attempt_number: int
    attempt_type: str
    prompt: str
    planned_evaluation_case: PlannedEvaluationCase | None = None
    tool_executions: list[ToolExecution]
    path_analysis: PathAnalysis
    path_adherence: PathAdherence | None = None
    final_response: str
    evaluation: AttackEvaluation
    path_decision: PathDecision | None = None


class AdaptiveRunResult(BaseModel):
    run_id: str = ""
    threat_id: str
    category: str
    max_variants: int
    attempts: list[AdaptiveAttempt]
    final_success: bool
    successful_attack_id: str | None
    path_coverage: PathCoverage
    summary: AdaptiveRunSummary | None = None
