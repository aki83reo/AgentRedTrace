import asyncio
import sys

import uvicorn
from fastapi import FastAPI

from api.routes import router

app = FastAPI(
    title="AgentRedTrace",
    version="0.1.0",
)

app.include_router(router)


@app.get("/health")
def health():
    """Report that the API process is running."""
    return {"status": "healthy"}


def run_api() -> None:
    """Start the customer support API."""
    uvicorn.run("main:app", host="127.0.0.1", port=8000)


def run_attacks() -> None:
    """Run the attack suite against the customer support agent."""
    from redteam.runner.attack_runner import AttackRunner

    asyncio.run(AttackRunner().run_all())


def run_adaptive() -> None:
    """Run the DATA-001 lineage using predefined variants."""
    from redteam.adaptive.adaptive_runner import AdaptiveAttackRunner
    from redteam.runner.attack_runner import AttackRunner

    try:
        asyncio.run(AdaptiveAttackRunner(AttackRunner()).run_data_001())
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc


def run_plan() -> None:
    """Run DATA-001, choose the next unexplored path, and stop."""
    from redteam.adaptive.adaptive_runner import AdaptiveAttackRunner
    from redteam.runner.attack_runner import AttackRunner

    try:
        asyncio.run(AdaptiveAttackRunner(AttackRunner()).run_data_001_plan())
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc


def run_explore() -> None:
    """Run DATA-001, execute one planned child, and write JSON plus a trace."""
    from redteam.adaptive.adaptive_runner import AdaptiveAttackRunner
    from redteam.runner.attack_runner import AttackRunner

    try:
        asyncio.run(AdaptiveAttackRunner(AttackRunner()).run_explore())
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "api"
    if command == "api":
        run_api()
    elif command == "attacks":
        run_attacks()
    elif command == "adaptive":
        run_adaptive()
    elif command == "plan":
        run_plan()
    elif command == "explore":
        run_explore()
    else:
        raise SystemExit(
            "Use: python main.py api   or   python main.py attacks"
            "   or   python main.py adaptive   or   python main.py plan"
            "   or   python main.py explore"
        )
