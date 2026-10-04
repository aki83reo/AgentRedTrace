import json

from pydantic import BaseModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from config import settings
from redteam.adaptive.models import PathAnalysis, PathCoverage
from redteam.planner.models import PathDecision
from redteam.prompts.path_planner import PATH_PLANNER_SYSTEM_PROMPT


class PathPlannerResponse(BaseModel):
    selected_path: list[str]
    reasoning: str
    selection_reason: str
    paths_considered: list[list[str]]
    should_continue: bool


class LLMPathPlanner:
    def __init__(self) -> None:
        """Use the same model settings as the customer support agent."""
        self.model_name = settings.openai_model

    async def plan(
        self,
        path_analysis: PathAnalysis,
        path_coverage: PathCoverage,
        attack_id: str,
        attack_name: str,
        category: str,
        expected_safe_behavior: str,
    ) -> PathDecision:
        """Choose one unexplored path, or stop when none remain."""
        if not path_coverage.unexplored_paths:
            return _no_paths_left(path_analysis)

        response = await self._ask(
            path_analysis,
            path_coverage,
            attack_id,
            attack_name,
            category,
            expected_safe_behavior,
        )
        return decision_from_response(response, path_analysis, path_coverage, self.model_name)

    async def _ask(
        self,
        path_analysis: PathAnalysis,
        path_coverage: PathCoverage,
        attack_id: str,
        attack_name: str,
        category: str,
        expected_safe_behavior: str,
    ) -> PathPlannerResponse:
        structured = self._chat_model().with_structured_output(PathPlannerResponse)
        raw = await structured.ainvoke(
            [
                SystemMessage(content=PATH_PLANNER_SYSTEM_PROMPT),
                HumanMessage(
                    content=_planner_input(
                        path_analysis,
                        path_coverage,
                        attack_id,
                        attack_name,
                        category,
                        expected_safe_behavior,
                    )
                ),
            ]
        )
        if isinstance(raw, PathPlannerResponse):
            return raw
        return PathPlannerResponse.model_validate(raw)

    def _chat_model(self) -> ChatOpenAI:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set.")
        kwargs = {
            "model": settings.openai_model,
            "api_key": settings.openai_api_key,
        }
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url
        return ChatOpenAI(**kwargs)


def decision_from_response(
    response: PathPlannerResponse,
    path_analysis: PathAnalysis,
    path_coverage: PathCoverage,
    model_name: str | None,
) -> PathDecision:
    """Accept the choice only when it is one of the unexplored paths."""
    selected = list(response.selected_path)
    allowed = _is_unexplored(selected, path_coverage.unexplored_paths)
    if not allowed:
        shown = " → ".join(selected) if selected else "none"
        return PathDecision(
            selected_path=None,
            previous_path=list(path_analysis.attempted_path),
            stopping_component=path_analysis.stopping_component,
            stopping_reason=path_analysis.stopping_reason,
            reasoning=response.reasoning,
            selection_reason=(
                f"Rejected selection {shown}. It is not in the unexplored path set."
            ),
            paths_considered=response.paths_considered,
            planner_type="llm",
            should_continue=False,
            model_name=model_name,
        )
    return PathDecision(
        selected_path=selected,
        previous_path=list(path_analysis.attempted_path),
        stopping_component=path_analysis.stopping_component,
        stopping_reason=path_analysis.stopping_reason,
        reasoning=response.reasoning,
        selection_reason=response.selection_reason,
        paths_considered=response.paths_considered,
        planner_type="llm",
        should_continue=response.should_continue,
        model_name=model_name,
    )


def _no_paths_left(path_analysis: PathAnalysis) -> PathDecision:
    return PathDecision(
        selected_path=None,
        previous_path=list(path_analysis.attempted_path),
        stopping_component=path_analysis.stopping_component,
        stopping_reason=path_analysis.stopping_reason,
        reasoning="No unexplored paths remain in the V1 path space.",
        selection_reason="No unexplored paths remain.",
        paths_considered=[],
        planner_type="skipped",
        should_continue=False,
        model_name=None,
    )


def _planner_input(
    path_analysis: PathAnalysis,
    path_coverage: PathCoverage,
    attack_id: str,
    attack_name: str,
    category: str,
    expected_safe_behavior: str,
) -> str:
    return "\n".join(
        [
            f"Threat ID:\n{attack_id}",
            f"Threat name:\n{attack_name}",
            f"Threat category:\n{category}",
            f"Expected safe behavior:\n{expected_safe_behavior}",
            "",
            f"Previous attempted path:\n{json.dumps(path_analysis.attempted_path)}",
            f"Successful components:\n{json.dumps(path_analysis.successful_components)}",
            f"Blocked components:\n{json.dumps(path_analysis.blocked_components)}",
            f"Failed components:\n{json.dumps(path_analysis.failed_components)}",
            f"Stopping component:\n{path_analysis.stopping_component or 'none'}",
            f"Stopping reason:\n{path_analysis.stopping_reason or 'none'}",
            "",
            f"Known tools:\n{json.dumps(path_coverage.known_tools)}",
            f"Untested tools:\n{json.dumps(path_analysis.untested_tools)}",
            f"Previously attempted paths:\n{json.dumps(path_coverage.attempted_paths)}",
            f"Unexplored paths:\n{json.dumps(path_coverage.unexplored_paths)}",
            "",
            "Select one path from Unexplored paths.",
        ]
    )


def _is_unexplored(path: list[str], unexplored: list[list[str]]) -> bool:
    key = tuple(path)
    return any(tuple(candidate) == key for candidate in unexplored)

