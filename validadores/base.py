from abc import ABC, abstractmethod
from typing import Optional


class ValidationRule(ABC):
    """Base class for all validation rules."""

    @property
    @abstractmethod
    def priority(self) -> int:
        """Priority of the rule (higher number = higher priority)."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the validation rule."""
        pass

    @abstractmethod
    def validate(self, gnb_text: str, ue_text: str, docker_text: str) -> Optional[str]:
        """
        Validate the generated configurations.

        Args:
            gnb_text: The gNB configuration text
            ue_text: The UE configuration text
            docker_text: The docker-compose configuration text

        Returns:
            None if validation passes, error message string if validation fails
        """
        pass


class ValidationManager:
    """Manages a collection of validation rules and executes them in priority order."""

    def __init__(self):
        self._rules = []

    def register_rule(self, rule: ValidationRule):
        """Register a validation rule."""
        self._rules.append(rule)
        # Sort rules by priority (descending) so higher priority rules run first
        self._rules.sort(key=lambda r: r.priority, reverse=True)

    def unregister_rule(self, rule_name: str):
        """Unregister a validation rule by name."""
        self._rules = [r for r in self._rules if r.name != rule_name]

    def validate_all(self, gnb_text: str, ue_text: str, docker_text: str) -> Optional[str]:
        """
        Execute all registered validation rules in priority order.

        Args:
            gnb_text: The gNB configuration text
            ue_text: The UE configuration text
            docker_text: The docker-compose configuration text

        Returns:
            None if all validations pass, error message from first failed validation
        """
        for rule in self._rules:
            error = rule.validate(gnb_text, ue_text, docker_text)
            if error is not None:
                return f"[{rule.name}] {error}"
        return None