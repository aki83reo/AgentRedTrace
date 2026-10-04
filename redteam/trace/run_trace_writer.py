import json
from pathlib import Path

from redteam.adaptive.models import AdaptiveAttempt, AdaptiveRunResult, PathCoverage
from redteam.planner.models import PathDecision


class RunTraceWriter:
    def __init__(self, path: Path) -> None:
        """Write one chronological trace file for this run."""
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._started = False

    def write_header(
        self,
        run_id: str,
        threat_id: str,
        category: str,
        max_executions: int,
    ) -> None:
        """Write the run heading."""
        self._write(
            _block(
                [
                    "=" * 60,
                    "AGENTREDTRACE — ADAPTIVE RUN TRACE",
                    "=" * 60,
                    "",
                    "Run ID:",
                    run_id,
                    "",
                    "Root Threat:",
                    threat_id,
                    "",
                    "Category:",
                    category,
                    "",
                    "Maximum Executions:",
                    str(max_executions),
                    "",
                ]
            )
        )

    def write_attempt(self, attempt: AdaptiveAttempt, coverage: PathCoverage) -> None:
        """Append one finished attempt, including coverage after that attempt."""
        kind = "ORIGINAL" if attempt.attempt_type == "original" else "PLANNED_PATH"
        lines = [
            "=" * 60,
            f"ATTEMPT {attempt.attempt_number} — {attempt.attack_id}",
            "=" * 60,
            "",
            "Type:",
            kind,
            "",
            "Parent:",
            attempt.parent_attack_id or "NONE",
            "",
        ]
        if attempt.attempt_number > 0 and attempt.root_attack_id:
            lines.extend(["Root:", attempt.root_attack_id, ""])
        if attempt.attempt_number == 0:
            lines.extend(["Prompt:", attempt.prompt, ""])
        case = attempt.planned_evaluation_case
        if case is not None:
            lines.extend(
                [
                    "-" * 60,
                    "PLANNED EVALUATION",
                    "-" * 60,
                    "",
                    "Planned Path:",
                    _path(case.planned_path),
                    "",
                    "Generated Instruction:",
                    case.generated_instruction,
                    "",
                ]
            )
        lines.extend(["-" * 60, "TARGET EXECUTION", "-" * 60, ""])
        if not attempt.tool_executions:
            lines.extend(["No tools were called.", ""])
        else:
            lines.extend(_tool_lines(attempt))
        analysis = attempt.path_analysis
        lines.extend(
            [
                "-" * 60,
                "TRAJECTORY ANALYSIS",
                "-" * 60,
                "",
                "Actual Path:",
                _path(analysis.attempted_path),
                "",
                "Reached:",
                _names(analysis.reachable_components),
                "",
                "Successful:",
                _names(analysis.successful_components),
                "",
                "Blocked:",
                _names(analysis.blocked_components),
                "",
                "Failed:",
                _names(analysis.failed_components),
                "",
                "Stopping Component:",
                analysis.stopping_component or "NONE",
                "",
                "Stopping Reason:",
                analysis.stopping_reason or "NONE",
                "",
            ]
        )
        adherence = attempt.path_adherence
        if adherence is not None:
            lines.extend(
                [
                    "-" * 60,
                    "PATH ADHERENCE",
                    "-" * 60,
                    "",
                    "Planned:",
                    _path(adherence.planned_path),
                    "",
                    "Actual:",
                    _path(adherence.actual_path),
                    "",
                    "Status:",
                    adherence.status.upper(),
                    "",
                    "Matched Steps:",
                    f"{adherence.matched_steps} of {adherence.planned_steps}",
                    "",
                    "Reason:",
                    adherence.reason,
                    "",
                ]
            )
        lines.extend(
            [
                "-" * 60,
                "JUDGE",
                "-" * 60,
                "",
                "Result:",
                _judge_word(attempt.evaluation.success),
                "",
                "Judge:",
                attempt.evaluation.judge_type,
                "",
                "Reason:",
                attempt.evaluation.reason,
                "",
                "-" * 60,
                "PATH COVERAGE AFTER ATTEMPT 0"
                if attempt.attempt_number == 0
                else "CUMULATIVE PATH COVERAGE",
                "-" * 60,
                "",
            ]
        )
        lines.extend(_coverage_lines(coverage))
        self._write(_block(lines))

    def write_planner(self, decision: PathDecision) -> None:
        """Append the planner decision that followed an attempt."""
        lines = [
            "-" * 60,
            "LLM PATH PLANNER",
            "-" * 60,
            "",
            "Selected Path:",
            _path(decision.selected_path or []),
            "",
            "Paths Considered:",
            _paths(decision.paths_considered),
            "",
            "Reasoning:",
            decision.reasoning,
            "",
            "Selection Reason:",
            decision.selection_reason,
            "",
            "Continue:",
            "YES" if decision.should_continue else "NO",
            "",
        ]
        if decision.model_name:
            lines.extend(["Model:", decision.model_name, ""])
        self._write(_block(lines))

    def write_summary(self, result: AdaptiveRunResult) -> None:
        """Append the closing summary for the attempts completed so far."""
        summary = result.summary
        lines = [
            "=" * 60,
            "RUN SUMMARY",
            "=" * 60,
            "",
            "Root Threat:",
            result.threat_id,
            "",
            "Attempts Executed:",
            str(len(result.attempts) if summary is None else summary.attempts_executed),
            "",
            "Attempt Lineage:",
            "",
            _lineage(result),
            "",
        ]
        for attempt in result.attempts:
            lines.extend(
                [
                    f"Attempt {attempt.attempt_number}:",
                    _judge_word(attempt.evaluation.success),
                    "",
                ]
            )
        observed = [] if summary is None else summary.paths_observed
        selected = [] if summary is None else summary.planner_paths_selected
        lines.extend(["Paths Actually Observed:"])
        if observed:
            for index, path in enumerate(observed, start=1):
                lines.append(f"{index}. {_path(path)}")
        else:
            lines.append("none")
        lines.extend(["", "Planner Decisions:"])
        if selected:
            for index, path in enumerate(selected, start=1):
                lines.append(f"{index}. {_path(path)}")
        else:
            lines.append("none")
        root_success = None if summary is None else summary.root_attack_success
        stop_reason = "NONE" if summary is None else summary.stop_reason
        lines.extend(
            [
                "",
                "Final Security Result:",
                _judge_word(root_success),
                "",
                "Stop Reason:",
                stop_reason,
                "",
                "=" * 60,
                "END TRACE",
                "=" * 60,
                "",
            ]
        )
        self._write(_block(lines))

    def _write(self, text: str) -> None:
        mode = "a" if self._started else "w"
        with self.path.open(mode, encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
        self._started = True


def _tool_lines(attempt: AdaptiveAttempt) -> list[str]:
    traces = {trace.sequence: trace for trace in attempt.path_analysis.component_traces}
    lines = []
    for execution in attempt.tool_executions:
        trace = traces.get(execution.sequence)
        status = trace.status.upper() if trace is not None else "UNKNOWN"
        reason = trace.reason if trace is not None else None
        lines.extend(
            [
                f"Tool {execution.sequence}:",
                execution.tool_name,
                "",
                "Arguments:",
                json.dumps(execution.arguments, indent=4),
                "",
                "Result:",
                json.dumps(execution.result, indent=4),
                "",
                "Status:",
                status,
                "",
            ]
        )
        if reason:
            lines.extend(["Reason:", reason, ""])
    return lines


def _coverage_lines(coverage: PathCoverage) -> list[str]:
    return [
        "Known Tools:",
        _names(coverage.known_tools),
        "",
        "Reached Tools:",
        _names(coverage.reached_tools),
        "",
        "Successful Tools:",
        _names(coverage.successful_tools),
        "",
        "Blocked Tools:",
        _names(coverage.blocked_tools),
        "",
        "Failed Tools:",
        _names(coverage.failed_tools),
        "",
        "Untested Tools:",
        _names(coverage.untested_tools),
        "",
        "Attempted Paths:",
        _paths(coverage.attempted_paths),
        "",
        "Unexplored Paths:",
        _paths(coverage.unexplored_paths),
        "",
    ]


def _lineage(result: AdaptiveRunResult) -> str:
    if len(result.attempts) == 1:
        return result.attempts[0].attack_id
    lines = [result.attempts[0].attack_id]
    for attempt in result.attempts[1:]:
        lines.append("    |")
        lines.append(f"    +-- {attempt.attack_id}")
    return "\n".join(lines)


def _block(lines: list[str]) -> str:
    return "\n".join(lines) + "\n"


def _path(path: list[str]) -> str:
    if not path:
        return "none"
    return " → ".join(path)


def _paths(paths: list[list[str]]) -> str:
    if not paths:
        return "none"
    return "\n".join(_path(path) for path in paths)


def _names(names: list[str]) -> str:
    if not names:
        return "none"
    return "\n".join(names)


def _judge_word(success: bool | None) -> str:
    if success is True:
        return "SUCCESS"
    if success is False:
        return "FAILED"
    return "NOT_EVALUATED"
