import json
import logging
import uuid

logger = logging.getLogger("redteamtrace")


def configure_logging() -> None:
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.propagate = False


def log_agent_started() -> None:
    logger.info("Agent started")


def log_agent_completed() -> None:
    logger.info("Agent completed")


def log_tool_requested(tool_name: str) -> None:
    logger.info("Tool requested: %s", tool_name)


def log_tool_executed(tool_name: str) -> None:
    logger.info("Tool executed: %s", tool_name)


def generate_ticket_id() -> str:
    return f"TKT-{uuid.uuid4().hex[:8].upper()}"


def format_tool_result(payload: dict) -> str:
    return json.dumps(payload)
