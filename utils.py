import json
import logging
import uuid
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("agentredtrace")


def configure_logging() -> None:
    """Send info logs to the terminal once."""
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.propagate = False


def log_agent_started() -> None:
    """Log that a chat run has started."""
    logger.info("[AGENT]\nProcessing request")


def log_agent_completed(response: str) -> None:
    """Log the final assistant text."""
    logger.info("[AGENT]\nFinal response:\n%s", response)


def log_tool_requested(tool_name: str, arguments: dict) -> None:
    """Log the tool name and the arguments the model requested."""
    logger.info(
        "[TOOL]\n%s\narguments:\n%s",
        tool_name,
        json.dumps(arguments, indent=4),
    )


def log_tool_result(payload: dict) -> None:
    """Log the structured result a tool returned."""
    logger.info("[RESULT]\n%s", json.dumps(payload, indent=4))


def generate_ticket_id() -> str:
    """Build a ticket id such as TKT-A12BC34D."""
    return f"TKT-{uuid.uuid4().hex[:8].upper()}"


def format_tool_result(payload: dict) -> str:
    """Turn a tool payload into a JSON string."""
    return json.dumps(payload)


def load_json(path: str | Path):
    """Read a JSON file and return the parsed value."""
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: str | Path, payload: dict) -> None:
    """Write a dictionary to a JSON file."""
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def generate_run_id() -> str:
    """Build a run id such as RUN-20261004-113500."""
    return datetime.now().strftime("RUN-%Y%m%d-%H%M%S")
