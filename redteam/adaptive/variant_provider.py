from abc import ABC, abstractmethod

from redteam.adaptive.models import AdaptiveAttempt

DATA_001_VARIANTS = [
    "<USER_PROVIDED_VARIANT_1>",
    "<USER_PROVIDED_VARIANT_2>",
]


class VariantProvider(ABC):
    @abstractmethod
    def get_next_variant(
        self,
        root_attack_id: str,
        history: list[AdaptiveAttempt],
    ) -> str | None:
        """Return the next prompt, or None when no variant remains."""


class FixedVariantProvider(VariantProvider):
    def __init__(self, variants: dict[str, list[str]] | None = None) -> None:
        """Store predefined prompts keyed by the root attack id."""
        self.variants = variants if variants is not None else {"DATA-001": DATA_001_VARIANTS}

    def get_next_variant(
        self,
        root_attack_id: str,
        history: list[AdaptiveAttempt],
    ) -> str | None:
        """Return the next unused predefined prompt for this root attack."""
        prompts = self.variants.get(root_attack_id, [])
        used = sum(1 for attempt in history if attempt.attempt_type == "fixed_variant")
        if used >= len(prompts):
            return None
        prompt = prompts[used]
        if _is_placeholder(prompt):
            raise RuntimeError(
                f"{root_attack_id} adaptive variants have not been configured."
            )
        return prompt


def _is_placeholder(prompt: str) -> bool:
    stripped = prompt.strip()
    return stripped.startswith("<") and stripped.endswith(">")
