from pydantic import BaseModel


class PathDecision(BaseModel):
    selected_path: list[str] | None
    previous_path: list[str]
    stopping_component: str | None
    stopping_reason: str | None
    reasoning: str
    selection_reason: str
    paths_considered: list[list[str]]
    planner_type: str = "llm"
    should_continue: bool
    model_name: str | None = None
