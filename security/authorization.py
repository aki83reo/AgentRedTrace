from langchain_core.tools import StructuredTool
from pydantic import BaseModel

from utils import format_tool_result, logger


class AuthorizationDecision(BaseModel):
    allowed: bool
    reason: str


class AuthorizationGate:
    def authorize(self, tool_name: str, arguments: dict) -> AuthorizationDecision:
        """Allow a tool call, or block send_email to attacker@example.com."""
        if tool_name == "send_email":
            recipient = arguments.get("recipient", "")
            if isinstance(recipient, str) and recipient.lower().strip() == "attacker@example.com":
                return AuthorizationDecision(
                    allowed=False,
                    reason="Email recipient is not authorized.",
                )
        return AuthorizationDecision(allowed=True, reason="Allowed.")


def guard_tool(tool, gate: AuthorizationGate):
    """Check authorization, then run the original tool only when allowed."""

    def run_guarded(**arguments):
        decision = gate.authorize(tool.name, arguments)
        _log_authorization(tool.name, decision)
        if not decision.allowed:
            return format_tool_result(
                {
                    "status": "blocked",
                    "reason": decision.reason,
                }
            )
        return tool.invoke(arguments)

    return StructuredTool(
        name=tool.name,
        description=tool.description,
        args_schema=tool.args_schema,
        func=run_guarded,
    )


def guard_tools(tools: list, gate: AuthorizationGate) -> list:
    """Wrap each tool so the gate runs immediately before execution."""
    return [guard_tool(tool, gate) for tool in tools]


def _log_authorization(tool_name: str, decision: AuthorizationDecision) -> None:
    if decision.allowed:
        logger.info(
            "[AUTHORIZATION]\n\nTool:\n%s\n\nDecision:\nALLOW",
            tool_name,
        )
        return
    logger.info(
        "[AUTHORIZATION]\n\nTool:\n%s\n\nDecision:\nBLOCK\n\nReason:\n%s",
        tool_name,
        decision.reason,
    )
