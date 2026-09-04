import os
import logging
from fpdf import FPDF
import yaml
from utilidades import extraer_bloque
import configuraciones
from validadores.base import ValidationManager
from validadores.gnb_validation import GNBValidationRule
from validadores.ue_validation import UEValidationRule
from validadores.docker_validation import DockerValidationRule

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("/tmp/5g_config_generator.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

## -- Validación sintáctica de los ficheros generados -- ##

# Initialize validation manager and register rules
_validation_manager = ValidationManager()
_validation_manager.register_rule(GNBValidationRule())
_validation_manager.register_rule(UEValidationRule())
_validation_manager.register_rule(DockerValidationRule())

logger.debug("Validation manager initialized with 3 rules")


def _validar_gnb(gnb_text):
    if "\t" in gnb_text:
        error_msg = "el fichero contiene tabuladores. YAML solo admite espacios."
        logger.debug(f"GNB validation failed: {error_msg}")
        return f"SYNTAX_ERROR [gnb_zmq.yaml]: {error_msg}"
    try:
        data = yaml.safe_load(gnb_text)
    except yaml.YAMLError as e:
        error_msg = f"estructura YAML inválida. Detalle: {e}"
        logger.debug(f"GNB validation failed: {error_msg}")
        return f"SYNTAX_ERROR [gnb_zmq.yaml]: {error_msg}"
    if not isinstance(data, dict):
        error_msg = "el contenido no es un documento YAML válido."
        logger.debug(f"GNB validation failed: {error_msg}")
        return f"SYNTAX_ERROR [gnb_zmq.yaml]: {error_msg}"
    for clave in GNB_CLAVES_OBLIGATORIAS:
        if clave not in data:
            error_msg = f"clave obligatoria ausente → '{clave}'."
            logger.debug(f"GNB validation failed: {error_msg}")
            return f"SYNTAX_ERROR [gnb_zmq.yaml]: {error_msg}"
    logger.debug("GNB validation passed")
    return None

def _validar_ue(ue_text):
    for num, linea in enumerate(ue_text.splitlines(), start=1):
        linea_limpia = linea.strip()
        if not linea_limpia or linea_limpia.startswith("#") or linea_limpia.startswith("["):
            continue
        if "=" not in linea_limpia:
            error_msg = (f"línea {num} malformada "
                        f"(se esperaba 'clave = valor') → '{linea_limpia}'.")
            logger.debug(f"UE validation failed: {error_msg}")
            return f"SYNTAX_ERROR [ue_zmq.conf]: {error_msg}"
    for seccion in SECCIONES_UE_OBLIGATORIAS:
        if seccion not in ue_text:
            error_msg = f"sección obligatoria ausente → '{seccion}'."
            logger.debug(f"UE validation failed: {error_msg}")
            return f"SYNTAX_ERROR [ue_zmq.conf]: {error_msg}"
    logger.debug("UE validation passed")
    return None

def _validar_docker(docker_text):
    try:
        data = yaml.safe_load(docker_text)
    except yaml.YAMLError as e:
        error_msg = f"estructura YAML inválida. Detalle: {e}"
        logger.debug(f"Docker validation failed: {error_msg}")
        return f"SYNTAX_ERROR [docker-compose.yml]: {error_msg}"
    if not isinstance(data, dict):
        error_msg = "el contenido no es un documento YAML válido."
        logger.debug(f"Docker validation failed: {error_msg}")
        return f"SYNTAX_ERROR [docker-compose.yml]: {error_msg}"
    if "services" not in data:
        error_msg = "clave obligatoria ausente → 'services'."
        logger.debug(f"Docker validation failed: {error_msg}")
        return f"SYNTAX_ERROR [docker-compose.yml]: {error_msg}"
    subscriber_db = None
    try:
        env_list = data["services"]["5gc"]["environment"]
        for entrada in env_list:
            if isinstance(entrada, str) and entrada.startswith("SUBSCRIBER_DB="):
                subscriber_db = entrada.split("=", 1)[1]
                break
    except (KeyError, TypeError):
        error_msg = "no se encontró el servicio '5gc' o su bloque 'environment'."
        logger.debug(f"Docker validation failed: {error_msg}")
        return f"SYNTAX_ERROR [docker-compose.yml]: {error_msg}"
    if subscriber_db is None:
        error_msg = "variable obligatoria ausente → 'SUBSCRIBER_DB'."
        logger.debug(f"Docker validation failed: {error_msg}")
        return f"SYNTAX_ERROR [docker-compose.yml]: {error_msg}"
    campos = subscriber_db.split(",")
    if len(campos) != 7:
        error_msg = "SUBSCRIBER_DB malformado."
        logger.debug(f"Docker validation failed: {error_msg}")
        return f"SYNTAX_ERROR [docker-compose.yml]: {error_msg}"
    logger.debug("Docker validation passed")
    return None

## -- Parseo de la respuesta del modelo -- ##

def parsear_respuesta(raw_text):
    """Extrae los bloques y detecta VALIDATION_ERROR."""
    logger.debug(f"Parsing model response ({len(raw_text)} chars)")
    if raw_text.strip().startswith("VALIDATION_ERROR"):
        error_msg = raw_text.strip()
        logger.warning(f"Validation error from model: {error_msg}")
        return None, error_msg

    gnb    = extraer_bloque(raw_text, "---START_GNB---",    "---END_GNB---")
    ue     = extraer_bloque(raw_text, "---START_UE---",     "---END_UE---")
    docker = extraer_bloque(raw_text, "---START_DOCKER---", "---END_DOCKER---")
    notes  = extraer_bloque(raw_text, "---START_NOTES---",  "---END_NOTES---")

    logger.debug(f"Extracted blocks - GNB: {len(gnb) if gnb else 0} chars, "
                 f"UE: {len(ue) if ue else 0} chars, "
                 f"Docker: {len(docker) if docker else 0} chars, "
                 f"Notes: {len(notes) if notes else 0} chars")

    if not all([gnb, ue, docker]):
        error_msg = "El modelo no devolvió la estructura completa."
        logger.warning(f"Response parsing failed: {error_msg}")
        return None, error_msg

    # Use the new validation system
    logger.debug("Running validation checks on extracted blocks")
    error = _validation_manager.validate_all(gnb, ue, docker)
    if error:
        logger.warning(f"Validation failed: {error}")
        return None, error

    logger.info("Response parsing and validation successful")
    return {"gnb": gnb, "ue": ue, "docker": docker, "notes": notes}, None


## -- Exportación de archivos y PDF de reporte -- #

def exportar(bloques, timestamp):
    logger.info(f"Exporting configuration files for timestamp {timestamp}")
    os.makedirs(configuraciones.RUTAS_SALIDA["gnb"],    exist_ok=True)
    os.makedirs(configuraciones.RUTAS_SALIDA["ue"],     exist_ok=True)
    os.makedirs(configuraciones.RUTAS_SALIDA["docker"], exist_ok=True)
    os.makedirs(configuraciones.RUTAS_SALIDA["pdf"],    exist_ok=True)

    archivos = {
        os.path.join(configuraciones.RUTAS_SALIDA["gnb"],    f"gnb_zmq.yaml"):        bloques["gnb"],
        os.path.join(configuraciones.RUTAS_SALIDA["ue"],     f"ue_zmq.conf"):         bloques["ue"],
        os.path.join(configuraciones.RUTAS_SALIDA["docker"], f"docker-compose.yml"):  bloques["docker"],
    }
    for ruta, contenido in archivos.items():
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(contenido)
        logger.debug(f"Exported file: {ruta} ({len(contenido)} chars)")
    logger.info("Configuration files exported successfully")
    print(f"  [✓] Archivos exportados")

    # PDF de reporte
    logger.info(f"Generating PDF report for timestamp {timestamp}")
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Courier", size=8)
    secciones = [
        (f"GNB ({timestamp})",    bloques["gnb"]),
        (f"UE ({timestamp})",     bloques["ue"]),
        (f"DOCKER ({timestamp})", bloques["docker"]),
        (f"NOTAS ({timestamp})",  bloques.get("notes", "")),
    ]
    for titulo, contenido in secciones:
        pdf.add_page()
        pdf.set_font("Courier", style="B", size=10)
        pdf.multi_cell(0, 10, txt=f"=== {titulo} ===", ln=True, align='C')
        pdf.set_font("Courier", size=8)
        pdf.ln(3)
        for linea in contenido.split('\n'):
            segura = linea.encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 4, txt=segura, ln=True)
    ruta_pdf = os.path.join(configuraciones.RUTAS_SALIDA["pdf"], f"despliegue_e2e_{timestamp}.pdf")
    pdf.output(ruta_pdf)
    logger.info(f"PDF report generated: {ruta_pdf}")
    print(f"  [✓] Reporte PDF: {ruta_pdf}")