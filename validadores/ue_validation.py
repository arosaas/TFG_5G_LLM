from .base import ValidationRule


class UEValidationRule(ValidationRule):
    """Validates UE configuration."""

    @property
    def priority(self) -> int:
        return 30  # High priority

    @property
    def name(self) -> str:
        return "UE_VALIDATION"

    def validate(self, gnb_text: str, ue_text: str, docker_text: str) -> Optional[str]:
        # Check for malformed lines (should be key = value or section/comment)
        for num, linea in enumerate(ue_text.splitlines(), start=1):
            linea_limpia = linea.strip()
            if not linea_limpia or linea_limpia.startswith("#") or linea_limpia.startswith("["):
                continue
            if "=" not in linea_limpia:
                return (f"línea {num} malformada "
                        f"(se esperaba 'clave = valor') → '{linea_limpia}'.")

        # Check for required sections
        required_sections = ["[rf]", "[rat.nr]", "[usim]", "[nas]"]
        for seccion in required_sections:
            if seccion not in ue_text:
                return f"sección obligatoria ausente → '{seccion}'."

        return None