import yaml
from .base import ValidationRule


class DockerValidationRule(ValidationRule):
    """Validates docker-compose configuration."""

    @property
    def priority(self) -> int:
        return 30  # High priority

    @property
    def name(self) -> str:
        return "DOCKER_VALIDATION"

    def validate(self, gnb_text: str, ue_text: str, docker_text: str) -> Optional[str]:
        # Check YAML structure
        try:
            data = yaml.safe_load(docker_text)
        except yaml.YAMLError as e:
            return f"estructura YAML inválida. Detalle: {e}"

        if not isinstance(data, dict):
            return "el contenido no es un documento YAML válido."

        # Check for required keys
        if "services" not in data:
            return "clave obligatoria ausente → 'services'."

        # Check for SUBSCRIBER_DB in 5gc service environment
        subscriber_db = None
        try:
            env_list = data["services"]["5gc"]["environment"]
            for entrada in env_list:
                if isinstance(entrada, str) and entrada.startswith("SUBSCRIBER_DB="):
                    subscriber_db = entrada.split("=", 1)[1]
                    break
        except (KeyError, TypeError):
            return "no se encontró el servicio '5gc' o su bloque 'environment'."

        if subscriber_db is None:
            return "variable obligatoria ausente → 'SUBSCRIBER_DB'."

        # Validate SUBSCRIBER_DB format
        campos = subscriber_db.split(",")
        if len(campos) != 7:
            return "SUBSCRIBER_DB malformado."

        return None