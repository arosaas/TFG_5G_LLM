# -- ARQUITECTURA HIBRIDA CAG+RAG PARA CONFIGURACIONES 5G -- #
# Autor: Alejandro R. Sarabia
# Fecha 06/2026

import os
from fpdf import FPDF
from utilidades import extraer_bloque
import configuraciones

## -- Parseo de la respuesta del modelo -- ##

def parsear_respuesta(raw_text):
    """Extrae los bloques y detecta VALIDATION_ERROR."""
    if raw_text.strip().startswith("VALIDATION_ERROR"):
        return None, raw_text.strip()

    gnb    = extraer_bloque(raw_text, "---START_GNB---",    "---END_GNB---")
    ue     = extraer_bloque(raw_text, "---START_UE---",     "---END_UE---")
    docker = extraer_bloque(raw_text, "---START_DOCKER---", "---END_DOCKER---")
    notes  = extraer_bloque(raw_text, "---START_NOTES---",  "---END_NOTES---")

    if not all([gnb, ue, docker]):
        return None, "El modelo no devolvió la estructura completa."

    return {"gnb": gnb, "ue": ue, "docker": docker, "notes": notes}, None

## -- Exportación de archivos y PDF de reporte -- #

def exportar(bloques, timestamp):
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
    print(f"  [✓] Archivos exportados")

    # PDF de reporte
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
        pdf.cell(0, 10, txt=f"=== {titulo} ===", ln=True, align='C')
        pdf.set_font("Courier", size=8)
        pdf.ln(3)
        for linea in contenido.split('\n'):
            segura = linea.encode('latin-1', 'replace').decode('latin-1')
            pdf.cell(0, 4, txt=segura, ln=True)
    ruta_pdf = os.path.join(configuraciones.RUTAS_SALIDA["pdf"], f"despliegue_e2e_{timestamp}.pdf")
    pdf.output(ruta_pdf)
    print(f"  [✓] Reporte PDF: {ruta_pdf}")
