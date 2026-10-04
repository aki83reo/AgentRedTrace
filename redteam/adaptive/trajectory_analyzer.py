from redteam.adaptive.models import ComponentTrace, PathAnalysis, PathCoverage
from redteam.models.attack import ToolExecution
from tools.customer_tool import CustomerTool
from tools.email_tool import EmailTool
from tools.ticket_tool import TicketTool

# Status values the current tools return when the operation finished.
_SUCCESS_STATUSES = {"success", "created", "sent"}


def known_tools() -> list[str]:
    """Return the tool names bound by the customer support agent, in bind order."""
    tools = [
        CustomerTool().as_tool(),
        TicketTool().as_tool(),
        EmailTool().as_tool(),
    ]
    return [tool.name for tool in tools]


def normalize_tool_status(tool_name: str, result: dict) -> tuple[str, bool, str | None]:
    """Map one tool result to status, whether it executed, and an optional reason.

    Blocked means the tool was requested and the gate stopped it.
    Success means the underlying operation finished.
    Failed means the operation ran and reported an error.
    """
    status = result.get("status")
    if status == "blocked":
        reason = result.get("reason")
        return "blocked", False, reason if isinstance(reason, str) else None

    error = result.get("error")
    if error is not None:
        return "failed", False, error if isinstance(error, str) else str(error)

    if isinstance(status, str) and status in _SUCCESS_STATUSES:
        return "success", True, None

    # get_customer returns the customer record itself when the lookup finishes.
    if tool_name == "get_customer" and result.get("customer_id"):
        return "success", True, None

    if isinstance(status, str) and status.lower() in {"failed", "error"}:
        reason = result.get("reason")
        return "failed", False, reason if isinstance(reason, str) else None

    return "unknown", False, None


class TrajectoryAnalyzer:
    def __init__(self, tool_names: list[str] | None = None) -> None:
        """Remember the tool inventory used to compute untested and unexplored paths."""
        self.tool_names = list(tool_names) if tool_names is not None else known_tools()

    def analyze(self, tool_executions: list[ToolExecution]) -> PathAnalysis:
        """Explain one observed tool trajectory. Does not judge attack success."""
        traces = [_trace(execution) for execution in tool_executions]
        attempted_path = [trace.component for trace in traces]
        reachable = _unique(attempted_path)
        stop = next((trace for trace in traces if trace.status in {"blocked", "failed"}), None)
        return PathAnalysis(
            attempted_path=attempted_path,
            reachable_components=reachable,
            successful_components=_names_with_status(traces, "success"),
            blocked_components=_names_with_status(traces, "blocked"),
            failed_components=_names_with_status(traces, "failed"),
            stopping_component=None if stop is None else stop.component,
            stopping_reason=None if stop is None else stop.reason,
            untested_tools=[name for name in self.tool_names if name not in reachable],
            component_traces=traces,
        )

    def coverage(self, analyses: list[PathAnalysis]) -> PathCoverage:
        """Aggregate observed paths and list the small V1 path space still untested."""
        attempted_paths = [analysis.attempted_path for analysis in analyses]
        reached = _in_inventory_order(self.tool_names, _flatten(analyses, "reachable_components"))
        successful = _in_inventory_order(self.tool_names, _flatten(analyses, "successful_components"))
        blocked = _in_inventory_order(self.tool_names, _flatten(analyses, "blocked_components"))
        failed = _in_inventory_order(self.tool_names, _flatten(analyses, "failed_components"))
        attempted_keys = {_path_key(path) for path in attempted_paths}
        candidates = _candidate_paths(self.tool_names)
        return PathCoverage(
            known_tools=list(self.tool_names),
            reached_tools=reached,
            successful_tools=successful,
            blocked_tools=blocked,
            failed_tools=failed,
            untested_tools=[name for name in self.tool_names if name not in reached],
            attempted_paths=attempted_paths,
            unique_paths_attempted=len(attempted_keys),
            unexplored_paths=[path for path in candidates if _path_key(path) not in attempted_keys],
        )


def _trace(execution: ToolExecution) -> ComponentTrace:
    status, executed, reason = normalize_tool_status(execution.tool_name, execution.result)
    return ComponentTrace(
        sequence=execution.sequence,
        component=execution.tool_name,
        component_type="tool",
        reached=True,
        executed=executed,
        status=status,
        reason=reason,
    )


def _names_with_status(traces: list[ComponentTrace], status: str) -> list[str]:
    return _unique(trace.component for trace in traces if trace.status == status)


def _unique(names) -> list[str]:
    seen = []
    for name in names:
        if name not in seen:
            seen.append(name)
    return seen


def _flatten(analyses: list[PathAnalysis], field: str) -> list[str]:
    names = []
    for analysis in analyses:
        names.extend(getattr(analysis, field))
    return names


def _in_inventory_order(tool_names: list[str], observed: list[str]) -> list[str]:
    seen = _unique(observed)
    ordered = [name for name in tool_names if name in seen]
    ordered.extend(name for name in seen if name not in tool_names)
    return ordered


def _candidate_paths(tool_names: list[str]) -> list[list[str]]:
    """Single-tool paths, then ordered two-tool paths. No repeated tools."""
    paths = [[name] for name in tool_names]
    for first in tool_names:
        for second in tool_names:
            if first != second:
                paths.append([first, second])
    return paths


def _path_key(path: list[str]) -> tuple[str, ...]:
    return tuple(path)
