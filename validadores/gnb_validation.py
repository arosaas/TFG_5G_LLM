import yaml
from .base import ValidationRule


class GNBValidationRule(ValidationRule):
    """Validates gNB configuration."""

    @property
    def priority(self) -> int:
        return 30  # High priority

    @property
    def name(self) -> str:
        return "GNB_VALIDATION"

    def validate(self, gnb_text: str, ue_text: str, docker_text: str) -> Optional[str]:
        # Check for tabs (YAML doesn't allow tabs)
        if "\t" in gnb_text:
            return "el fichero contiene tabuladores. YAML solo admite espacios."

        # Check YAML structure
        try:
            data = yaml.safe_load(gnb_text)
        except yaml.YAMLError as e:
            return f"estructura YAML inválida. Detalle: {e}"

        if not isinstance(data, dict):
            return "el contenido no es un documento YAML válido."

        # Check for required keys
        required_keys = ["cu_cp", "ru_sdr", "cell_cfg"]
        for key in required_keys:
            if key not in data:
                return f"clave obligatoria ausente → '{key}'."

        return None