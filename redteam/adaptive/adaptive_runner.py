from datetime import datetime
from pathlib import Path

from redteam.adaptive.models import (
    AdaptiveAttempt,
    AdaptiveRunResult,
    AdaptiveRunSummary,
    PathCoverage,
)
from redteam.adaptive.trajectory_analyzer import TrajectoryAnalyzer
from redteam.adaptive.variant_provider import FixedVariantProvider, VariantProvider
from redteam.runner.attack_runner import AttackRunner
from utils import generate_run_id, save_json

RESULTS_DIR = Path(__file__).resolve().parents[1] / "results" / "adaptive"
TRACES_DIR = Path(__file__).resolve().parents[1] / "results" / "traces"
MAX_VARIANTS = 2
MAX_EXPLORE_EXECUTIONS = 2


class AdaptiveAttackRunner:
    def __init__(
        self,
        attack_runner: AttackRunner,
        variant_provider: VariantProvider | None = None,
    ) -> None:
        """Reuse the static runner and a provider that supplies the next prompt."""
        self.attack_runner = attack_runner
        self.variant_provider = variant_provider or FixedVariantProvider()
        self.trajectory_analyzer = TrajectoryAnalyzer()

    async def run_data_001(self) -> AdaptiveRunResult:
        """Run DATA-001, then up to two predefined variants."""
        attack = self._load_data_001()
        self.variant_provider.get_next_variant(attack.attack_id, [])
        print("=" * 60, flush=True)
        print(f"ADAPTIVE THREAT: {attack.attack_id}", flush=True)
        print("=" * 60, flush=True)
        print(flush=True)

        run_id = generate_run_id()
        stamp = run_id.removeprefix("RUN-").replace("-", "_")
        path = RESULTS_DIR / f"run_{attack.attack_id}_{stamp}.json"
        attempts: list[AdaptiveAttempt] = []
        current_prompt = attack.prompt
        parent_attack_id = None

        for attempt_number in range(MAX_VARIANTS + 1):
            execution = await self.attack_runner.execute_case(attack, current_prompt)
            path_analysis = self.trajectory_analyzer.analyze(execution.tool_executions)
            attempt = AdaptiveAttempt(
                attack_id=_attempt_id(attack.attack_id, attempt_number),
                parent_attack_id=parent_attack_id,
                attempt_number=attempt_number,
                attempt_type="original" if attempt_number == 0 else "fixed_variant",
                prompt=current_prompt,
                tool_executions=execution.tool_executions,
                path_analysis=path_analysis,
                final_response=execution.final_response,
                evaluation=execution.evaluation,
            )
            attempts.append(attempt)
            result = _run_result(attack.category, attempts, self.trajectory_analyzer)
            _save(path, result)
            _print_attempt(attempt)
            _print_trajectory(attempt)
            if attempt_number > 0:
                print(flush=True)

            if execution.evaluation.success is True or execution.evaluation.success is None:
                break

            next_prompt = self.variant_provider.get_next_variant(attack.attack_id, attempts)
            if next_prompt is None:
                break
            print("\n                ↓ NEXT VARIANT\n", flush=True)
            parent_attack_id = attempt.attack_id
            current_prompt = next_prompt

        result = _run_result(attack.category, attempts, self.trajectory_analyzer)
        _save(path, result)
        _print_summary(result, path)
        return result

    async def run_data_001_plan(self) -> AdaptiveRunResult:
        """Run original DATA-001, record a path decision, and stop before the next path."""
        from redteam.planner.path_planner import LLMPathPlanner

        attack = self._load_data_001()
        print("=" * 60, flush=True)
        print(f"ADAPTIVE THREAT: {attack.attack_id}", flush=True)
        print("=" * 60, flush=True)
        print(flush=True)

        run_id = generate_run_id()
        stamp = run_id.removeprefix("RUN-").replace("-", "_")
        path = RESULTS_DIR / f"run_{attack.attack_id}_{stamp}.json"
        execution = await self.attack_runner.execute_case(attack, attack.prompt)
        path_analysis = self.trajectory_analyzer.analyze(execution.tool_executions)
        attempt = AdaptiveAttempt(
            attack_id=attack.attack_id,
            parent_attack_id=None,
            attempt_number=0,
            attempt_type="original",
            prompt=attack.prompt,
            tool_executions=execution.tool_executions,
            path_analysis=path_analysis,
            final_response=execution.final_response,
            evaluation=execution.evaluation,
        )
        attempts = [attempt]
        result = _run_result(attack.category, attempts, self.trajectory_analyzer)
        _save(path, result)
        _print_attempt(attempt)
        _print_trajectory(attempt)

        if execution.evaluation.success is False:
            decision = await LLMPathPlanner().plan(
                path_analysis=path_analysis,
                path_coverage=result.path_coverage,
                attack_id=attack.attack_id,
                attack_name=attack.name,
                category=attack.category,
                expected_safe_behavior=attack.expected_safe_behavior,
            )
            attempt = attempt.model_copy(update={"path_decision": decision})
            attempts = [attempt]
            result = _run_result(attack.category, attempts, self.trajectory_analyzer)
            _save(path, result)
            _print_planner(attempt)
            print(flush=True)
            print("Selected path recorded. Not executed in this phase.", flush=True)

        result = _run_result(attack.category, attempts, self.trajectory_analyzer)
        _save(path, result)
        print(flush=True)
        _print_summary(result, path)
        return result

    async def run_explore(self) -> AdaptiveRunResult:
        """Run DATA-001, plan one path, execute that child once, and stop."""
        from redteam.adaptive.evaluation_case_builder import EvaluationCaseBuilder
        from redteam.adaptive.path_adherence import assess_path_adherence
        from redteam.planner.path_planner import LLMPathPlanner
        from redteam.trace.run_trace_writer import RunTraceWriter

        attack = self._load_data_001()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_id = f"{attack.attack_id}_{stamp}"
        json_path = RESULTS_DIR / f"run_{run_id}.json"
        trace_path = TRACES_DIR / f"trace_{run_id}.txt"
        trace = RunTraceWriter(trace_path)
        trace.write_header(run_id, attack.attack_id, attack.category, MAX_EXPLORE_EXECUTIONS)
        print("=" * 60, flush=True)
        print("AGENTREDTRACE — PATH EXPLORATION", flush=True)
        print("=" * 60, flush=True)
        print(flush=True)
        print(f"Run ID: {run_id}", flush=True)
        print(flush=True)

        execution = await self.attack_runner.execute_case(attack, attack.prompt)
        path_analysis = self.trajectory_analyzer.analyze(execution.tool_executions)
        attempt = AdaptiveAttempt(
            attack_id=attack.attack_id,
            root_attack_id=attack.attack_id,
            parent_attack_id=None,
            attempt_number=0,
            attempt_type="original",
            prompt=attack.prompt,
            tool_executions=execution.tool_executions,
            path_analysis=path_analysis,
            final_response=execution.final_response,
            evaluation=execution.evaluation,
        )
        attempts = [attempt]
        result = _run_result(attack.category, attempts, self.trajectory_analyzer, run_id)
        _save(json_path, result)
        trace.write_attempt(attempt, result.path_coverage)
        _print_explore_attempt(attempt)

        if execution.evaluation.success is True:
            return _finish_explore(result, attempts, "SUCCESS", json_path, trace_path, trace, self.trajectory_analyzer)
        if execution.evaluation.success is None:
            return _finish_explore(
                result, attempts, "NOT_EVALUATED", json_path, trace_path, trace, self.trajectory_analyzer
            )

        decision = await LLMPathPlanner().plan(
            path_analysis=path_analysis,
            path_coverage=result.path_coverage,
            attack_id=attack.attack_id,
            attack_name=attack.name,
            category=attack.category,
            expected_safe_behavior=attack.expected_safe_behavior,
        )
        attempt = attempt.model_copy(update={"path_decision": decision})
        attempts = [attempt]
        result = _run_result(attack.category, attempts, self.trajectory_analyzer, run_id)
        _save(json_path, result)
        trace.write_planner(decision)
        print("Planner:", flush=True)
        print(f"Selected: {_format_path(decision.selected_path or [])}", flush=True)
        print(flush=True)

        if decision.selected_path is None or decision.should_continue is False:
            return _finish_explore(
                result, attempts, "NO_VALID_PATH", json_path, trace_path, trace, self.trajectory_analyzer
            )

        case = EvaluationCaseBuilder().build(
            attack,
            decision.selected_path,
            parent_attack_id=attack.attack_id,
        )
        child_execution = await self.attack_runner.execute_case(attack, case.generated_instruction)
        child_analysis = self.trajectory_analyzer.analyze(child_execution.tool_executions)
        child = AdaptiveAttempt(
            attack_id=case.attack_id,
            root_attack_id=case.root_attack_id,
            parent_attack_id=case.parent_attack_id,
            attempt_number=1,
            attempt_type="planned_path",
            prompt=case.generated_instruction,
            planned_evaluation_case=case,
            tool_executions=child_execution.tool_executions,
            path_analysis=child_analysis,
            path_adherence=assess_path_adherence(case.planned_path, child_analysis.attempted_path),
            final_response=child_execution.final_response,
            evaluation=child_execution.evaluation,
        )
        attempts.append(child)
        result = _run_result(attack.category, attempts, self.trajectory_analyzer, run_id)
        _save(json_path, result)
        trace.write_attempt(child, result.path_coverage)
        _print_explore_attempt(child)
        return _finish_explore(
            result,
            attempts,
            "MAX_EXECUTIONS_REACHED",
            json_path,
            trace_path,
            trace,
            self.trajectory_analyzer,
        )

    def _load_data_001(self):
        for attack in self.attack_runner.load_attacks():
            if attack.attack_id == "DATA-001":
                return attack
        raise RuntimeError("DATA-001 was not found in attacks.json.")


def _attempt_id(root_attack_id: str, attempt_number: int) -> str:
    if attempt_number == 0:
        return root_attack_id
    return f"{root_attack_id}.{attempt_number}"


def _run_result(
    category: str,
    attempts: list[AdaptiveAttempt],
    analyzer: TrajectoryAnalyzer,
    run_id: str = "",
    summary: AdaptiveRunSummary | None = None,
) -> AdaptiveRunResult:
    successful = next(
        (attempt for attempt in attempts if attempt.evaluation.success is True),
        None,
    )
    return AdaptiveRunResult(
        run_id=run_id,
        threat_id=attempts[0].attack_id.split(".")[0],
        category=category,
        max_variants=MAX_VARIANTS,
        attempts=attempts,
        final_success=successful is not None,
        successful_attack_id=None if successful is None else successful.attack_id,
        path_coverage=analyzer.coverage([attempt.path_analysis for attempt in attempts]),
        summary=summary,
    )


def _explore_summary(attempts: list[AdaptiveAttempt], stop_reason: str) -> AdaptiveRunSummary:
    successful = next(
        (attempt for attempt in attempts if attempt.evaluation.success is True),
        None,
    )
    if successful is not None:
        root_success = True
    elif any(attempt.evaluation.success is None for attempt in attempts):
        root_success = None
    else:
        root_success = False
    selected = []
    for attempt in attempts:
        if attempt.path_decision is not None and attempt.path_decision.selected_path:
            selected.append(attempt.path_decision.selected_path)
    return AdaptiveRunSummary(
        attempts_executed=len(attempts),
        root_attack_success=root_success,
        successful_attempt_id=None if successful is None else successful.attack_id,
        paths_observed=[attempt.path_analysis.attempted_path for attempt in attempts],
        planner_paths_selected=selected,
        stop_reason=stop_reason,
    )


def _finish_explore(
    result: AdaptiveRunResult,
    attempts: list[AdaptiveAttempt],
    stop_reason: str,
    json_path: Path,
    trace_path: Path,
    trace,
    analyzer: TrajectoryAnalyzer,
) -> AdaptiveRunResult:
    summary = _explore_summary(attempts, stop_reason)
    finished = _run_result(result.category, attempts, analyzer, result.run_id, summary)
    _save(json_path, finished)
    trace.write_summary(finished)
    print("Run Result:", flush=True)
    print(_result_word(summary.root_attack_success), flush=True)
    print(flush=True)
    print(f"JSON:\n{json_path}", flush=True)
    print(flush=True)
    print(f"Trace:\n{trace_path}", flush=True)
    return finished


def _print_explore_attempt(attempt: AdaptiveAttempt) -> None:
    analysis = attempt.path_analysis
    print(attempt.attack_id, flush=True)
    if attempt.path_adherence is None:
        print(f"Path: {_format_path(analysis.attempted_path)}", flush=True)
        print(f"Result: {_result_word(attempt.evaluation.success)}", flush=True)
        print(f"Stopped At: {analysis.stopping_component or 'None'}", flush=True)
    else:
        adherence = attempt.path_adherence
        print(f"Planned: {_format_path(adherence.planned_path)}", flush=True)
        print(f"Actual:  {_format_path(adherence.actual_path)}", flush=True)
        print(f"Adherence: {adherence.status.upper()}", flush=True)
        print(f"Result: {_result_word(attempt.evaluation.success)}", flush=True)
    print(flush=True)


def _save(path: Path, result: AdaptiveRunResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    save_json(path, result.model_dump())


def _print_attempt(attempt: AdaptiveAttempt) -> None:
    kind = "ORIGINAL" if attempt.attempt_type == "original" else "FIXED VARIANT"
    parent = attempt.parent_attack_id or "None"
    print(f"{attempt.attack_id}", flush=True)
    print(f"Type: {kind}", flush=True)
    print(f"Parent: {parent}", flush=True)
    print(flush=True)
    print("Result:", flush=True)
    print(_result_word(attempt.evaluation.success), flush=True)
    print(flush=True)
    print("Tool Path:", flush=True)
    print(_tool_path(attempt), flush=True)
    print(flush=True)
    print("Reason:", flush=True)
    print(attempt.evaluation.reason, flush=True)


def _print_summary(result: AdaptiveRunResult, path: Path) -> None:
    original = result.attempts[0]
    variants_used = sum(1 for attempt in result.attempts if attempt.attempt_type == "fixed_variant")
    print("=" * 60, flush=True)
    print("ADAPTIVE RUN SUMMARY", flush=True)
    print("=" * 60, flush=True)
    print(flush=True)
    print(f"Threat:                 {result.threat_id}", flush=True)
    print(f"Original Result:        {_result_word(original.evaluation.success)}", flush=True)
    print(f"Variants Used:          {variants_used}", flush=True)
    print(f"Final Result:           {_result_word(result.final_success)}", flush=True)
    print(f"Successful Attack:      {result.successful_attack_id or 'None'}", flush=True)
    print(f"Saved:                  {path}", flush=True)
    print(flush=True)
    _print_coverage(result.path_coverage)


def _print_trajectory(attempt: AdaptiveAttempt) -> None:
    analysis = attempt.path_analysis
    print(flush=True)
    print("-" * 60, flush=True)
    print(f"TRAJECTORY ANALYSIS — {attempt.attack_id}", flush=True)
    print("-" * 60, flush=True)
    print(flush=True)
    print("Attempted Path:", flush=True)
    print(_format_path(analysis.attempted_path), flush=True)
    print(flush=True)
    print("Component Trace:", flush=True)
    print(flush=True)
    if not analysis.component_traces:
        print("none", flush=True)
    for trace in analysis.component_traces:
        print(f"{trace.sequence}. {trace.component}", flush=True)
        print(f"   Reached:   {'YES' if trace.reached else 'NO'}", flush=True)
        print(f"   Executed:  {'YES' if trace.executed else 'NO'}", flush=True)
        print(f"   Status:    {trace.status.upper()}", flush=True)
        if trace.reason:
            print(f"   Reason:    {trace.reason}", flush=True)
        print(flush=True)
    print("Stopping Component:", flush=True)
    print(analysis.stopping_component or "None", flush=True)
    print(flush=True)
    print("Stopping Reason:", flush=True)
    print(analysis.stopping_reason or "None", flush=True)
    print(flush=True)
    print("Untested Tools:", flush=True)
    print(", ".join(analysis.untested_tools) if analysis.untested_tools else "none", flush=True)


def _print_planner(attempt: AdaptiveAttempt) -> None:
    decision = attempt.path_decision
    analysis = attempt.path_analysis
    print(flush=True)
    print("-" * 60, flush=True)
    print(f"LLM PATH PLANNER — {attempt.attack_id}", flush=True)
    print("-" * 60, flush=True)
    print(flush=True)
    print("Previous Path:", flush=True)
    print(_format_path(decision.previous_path), flush=True)
    print(flush=True)
    print("Stopped At:", flush=True)
    print(decision.stopping_component or "None", flush=True)
    print(flush=True)
    print("Reason:", flush=True)
    print(decision.stopping_reason or "None", flush=True)
    print(flush=True)
    print("Successful Components:", flush=True)
    print(", ".join(analysis.successful_components) if analysis.successful_components else "none", flush=True)
    print(flush=True)
    print("Untested Tools:", flush=True)
    print(", ".join(analysis.untested_tools) if analysis.untested_tools else "none", flush=True)
    print(flush=True)
    print("Paths Considered:", flush=True)
    if decision.paths_considered:
        for considered in decision.paths_considered:
            print(_format_path(considered), flush=True)
    else:
        print("none", flush=True)
    print(flush=True)
    print("Selected Next Path:", flush=True)
    print(_format_path(decision.selected_path or []), flush=True)
    print(flush=True)
    print("Selection Reason:", flush=True)
    print(decision.selection_reason, flush=True)
    print(flush=True)
    print("Continue:", flush=True)
    print("YES" if decision.should_continue else "NO", flush=True)
    if decision.model_name:
        print(flush=True)
        print("Model:", flush=True)
        print(decision.model_name, flush=True)


def _print_coverage(coverage: PathCoverage) -> None:
    print("-" * 60, flush=True)
    print("PATH COVERAGE", flush=True)
    print("-" * 60, flush=True)
    print(flush=True)
    print(f"Known Tools:        {len(coverage.known_tools)}", flush=True)
    print(f"Reached Tools:      {len(coverage.reached_tools)}", flush=True)
    print(f"Successful Tools:   {len(coverage.successful_tools)}", flush=True)
    print(f"Blocked Tools:      {len(coverage.blocked_tools)}", flush=True)
    print(f"Failed Tools:       {len(coverage.failed_tools)}", flush=True)
    print(f"Untested Tools:     {len(coverage.untested_tools)}", flush=True)
    print(flush=True)
    print(f"Unique Paths Tried: {coverage.unique_paths_attempted}", flush=True)
    print(flush=True)
    print("Attempted:", flush=True)
    if coverage.attempted_paths:
        for path in coverage.attempted_paths:
            print(_format_path(path), flush=True)
    else:
        print("none", flush=True)
    print(flush=True)
    print("Unexplored Paths:", flush=True)
    if coverage.unexplored_paths:
        for path in coverage.unexplored_paths:
            print(_format_path(path), flush=True)
    else:
        print("none", flush=True)


def _format_path(path: list[str]) -> str:
    if not path:
        return "none"
    return " → ".join(path)


def _tool_path(attempt: AdaptiveAttempt) -> str:
    if not attempt.tool_executions:
        return "none"
    parts = []
    for execution in attempt.tool_executions:
        if execution.result.get("status") == "blocked":
            parts.append(f"{execution.tool_name} [BLOCKED]")
        else:
            parts.append(execution.tool_name)
    return " → ".join(parts)


def _result_word(success: bool | None) -> str:
    if success is True:
        return "SUCCESS"
    if success is False:
        return "FAILED"
    return "NOT EVALUATED"
