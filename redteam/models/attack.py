from pydantic import BaseModel


class AttackCase(BaseModel):
    attack_id: str
    category: str
    name: str
    prompt: str
    expected_safe_behavior: str
    severity: str


class ToolExecution(BaseModel):
    sequence: int
    tool_name: str
    arguments: dict
    result: dict


class AttackEvaluation(BaseModel):
    success: bool | None
    judge_type: str
    reason: str


class AttackResult(BaseModel):
    attack_id: str
    category: str
    name: str
    prompt: str
    expected_safe_behavior: str
    final_response: str
    status: str
    tool_executions: list[ToolExecution]
    evaluation: AttackEvaluation | None = None
