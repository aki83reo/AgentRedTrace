import json
from pathlib import Path

from langchain_core.messages import ToolMessage

from agent.customer_support_agent import CustomerSupportAgent
from redteam.judge.deterministic_judge import DeterministicAttackJudge
from redteam.models.attack import AttackCase, AttackResult, ToolExecution
from utils import generate_run_id, load_json, save_json

ATTACKS_PATH = Path(__file__).resolve().parents[1] / "datasets" / "attacks.json"
RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"


class AttackRunner:
    def __init__(self) -> None:
        """Create the target agent and the deterministic judge."""
        self.target_agent = CustomerSupportAgent()
        self.judge = DeterministicAttackJudge()

    def load_attacks(self) -> list[AttackCase]:
        """Load attacks.json into attack cases."""
        records = load_json(ATTACKS_PATH)
        return [AttackCase.model_validate(record) for record in records]

    async def execute_case(self, attack: AttackCase, prompt: str) -> AttackResult:
        """Run one prompt through the target and judge it with this attack's rule."""
        final_response = await self.target_agent.run(prompt)
        result = AttackResult(
            attack_id=attack.attack_id,
            category=attack.category,
            name=attack.name,
            prompt=prompt,
            expected_safe_behavior=attack.expected_safe_behavior,
            final_response=final_response,
            status="completed",
            tool_executions=self._capture_tool_executions(self.target_agent.messages),
        )
        result.evaluation = self.judge.evaluate(attack, result)
        return result

    async def run_attack(self, attack: AttackCase) -> AttackResult:
        """Execute one attack, record its tool path, and judge that path."""
        self._print_header(attack)
        result = await self.execute_case(attack, attack.prompt)
        self._print_judgment(result)
        return result

    async def run_all(self) -> None:
        """Run every attack, save the judged results, and print the summary."""
        results = []
        for attack in self.load_attacks():
            results.append(await self.run_attack(attack))

        run_id = generate_run_id()
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        filename = "run_" + run_id.removeprefix("RUN-").replace("-", "_") + ".json"
        path = RESULTS_DIR / filename
        save_json(
            path,
            {
                "run_id": run_id,
                "results": [result.model_dump() for result in results],
            },
        )
        print(f"Saved results to {path}", flush=True)
        self._print_summary(results)

    def _capture_tool_executions(self, messages) -> list[ToolExecution]:
        calls = {}
        for message in messages:
            for tool_call in getattr(message, "tool_calls", None) or []:
                calls[tool_call["id"]] = tool_call

        executions = []
        for message in messages:
            if not isinstance(message, ToolMessage):
                continue
            tool_call = calls.get(message.tool_call_id, {})
            executions.append(
                ToolExecution(
                    sequence=len(executions) + 1,
                    tool_name=message.name or tool_call.get("name", ""),
                    arguments=tool_call.get("args") or {},
                    result=self._parse_tool_result(message.content),
                )
            )
        return executions

    def _parse_tool_result(self, content) -> dict:
        if isinstance(content, dict):
            return content
        if isinstance(content, str):
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                return {"value": content}
            if isinstance(parsed, dict):
                return parsed
        return {"value": str(content)}

    def _print_header(self, attack: AttackCase) -> None:
        print("=" * 50, flush=True)
        print(f"{attack.attack_id} — {attack.name}", flush=True)
        print("=" * 50, flush=True)
        print(flush=True)

    def _print_judgment(self, result: AttackResult) -> None:
        evaluation = result.evaluation
        print("PATH", flush=True)
        print(flush=True)
        if not result.tool_executions:
            print("No tools executed", flush=True)
        else:
            for execution in result.tool_executions:
                print(f"{execution.sequence}. {execution.tool_name}", flush=True)
        print(flush=True)
        print("JUDGE", flush=True)
        print(flush=True)
        print(f"Success: {self._success_word(evaluation.success)}", flush=True)
        print(f"Judge: {evaluation.judge_type}", flush=True)
        print(flush=True)
        print("Reason:", flush=True)
        print(evaluation.reason, flush=True)
        print(flush=True)

    def _print_summary(self, results: list[AttackResult]) -> None:
        print("Attack     Result", flush=True)
        print("-" * 25, flush=True)
        for result in results:
            print(
                f"{result.attack_id:<10} {self._summary_word(result.evaluation.success)}",
                flush=True,
            )

    def _success_word(self, success: bool | None) -> str:
        if success is True:
            return "TRUE"
        if success is False:
            return "FALSE"
        return "NOT EVALUATED"

    def _summary_word(self, success: bool | None) -> str:
        if success is True:
            return "SUCCESS"
        if success is False:
            return "FAILURE"
        return "NOT EVALUATED"
