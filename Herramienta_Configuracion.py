# --- ARQUITECTURA HÍBRIDA CAG+RAG PARA CONFIGURACIONES 5G ---
# Autor: Alejandro R. Sarabia

from google import genai
from google.genai import types
import os
import numpy as np
import time
import pickle
import re
from fpdf import FPDF
import PyPDF2
from dotenv import load_dotenv

load_dotenv()

# ── Configuración global ──────────────────────────────────────────────────────

client = genai.Client(api_key="")
MODEL_GEN = "gemini-2.5-flash"
MODEL_EMB = "gemini-embedding-001"

RUTAS_CAG = [
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/docker-compose.yml",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/gnb_zmq.yaml",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/ue_zmq.conf",
]
RUTAS_RAG = [
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/ts_123501v160600p.pdf",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/O-RAN.WG1.TR.Use-Cases-Analysis-Report-R005-v19.00-1.pdf",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/ejemplos_configuraciones2_5g.pdf",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/ts_123501v150200p.pdf",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/ejemplos_configuraciones_5g.pdf",
#   "/home/alejandroro/TFG_5G_LLM/CONFIGS/2406.01485v1.pdf",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/1285613.pdf",
#    "/home/alejandroro/TFG_5G_LLM/CONFIGS/267704.2677053.pdf",
#    "/home/alejandroro/TFG_5G_LLM/CONFIGS/AI-Driven_Zero_Touch_Network_and_Service_Management.pdf",
#    "/home/alejandroro/TFG_5G_LLM/CONFIGS/Comparative_E2E_Performance_Analysis_O-RAN.pdf",
#    "/home/alejandroro/TFG_5G_LLM/CONFIGS/Control_Plane_Performance_Benchmarking.pdf",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/getPDF.pdf",
#    "/home/alejandroro/TFG_5G_LLM/CONFIGS/LLM-enabled_Intent-driven_Service_Configuration.pdf",
]
RUTAS_SALIDA = {
    "gnb":    "/home/alejandroro/TFG_5G_LLM/srsRAN_Project/build/apps/gnb",
    "ue":     "/home/alejandroro/TFG_5G_LLM/srsRAN_4G/build/srsue",
    "docker": "/home/alejandroro/TFG_5G_LLM/srsRAN_Project/docker",
    "pdf":    "/home/alejandroro/TFG_5G_LLM/DESPLIEGUES",
}
BD_LOCAL = "base_datos_5g_tfg.pkl"
TOP_K    = 5   # chunks RAG recuperados por consulta
CHUNK_SZ = 800 # caracteres por chunk (chunking fino)

# ── Utilidades ────────────────────────────────────────────────────────────────

def sim_cos(v1, v2):
    n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
    return float(np.dot(v1, v2) / (n1 * n2)) if n1 and n2 else 0.0

def extraer_bloque(texto, inicio, fin):
    try:
        return texto.split(inicio)[1].split(fin)[0].strip()
    except IndexError:
        return ""

def chunk_texto(texto, nombre, tam=CHUNK_SZ):
    """Divide un texto largo en chunks solapados para mejor recuperación."""
    chunks = []
    paso = int(tam * 0.8)  # 20 % de solapamiento
    for i, inicio in enumerate(range(0, len(texto), paso)):
        fragmento = texto[inicio:inicio + tam]
        if fragmento.strip():
            chunks.append({"nombre": f"{nombre}__chunk{i}", "texto": fragmento})
    return chunks

# ── Carga CAG ─────────────────────────────────────────────────────────────────

def cargar_cag(rutas):
    contexto = ""
    for ruta in rutas:
        if os.path.exists(ruta):
            with open(ruta, 'r', encoding='utf-8') as f:
                contexto += f"\n--- PLANTILLA: {os.path.basename(ruta)} ---\n{f.read()}\n"
        else:
            print(f"  [WARN] CAG no encontrado: {os.path.basename(ruta)}")
    return contexto

# ── Carga y vectorización RAG ─────────────────────────────────────────────────

def cargar_bd(ruta_local):
    if os.path.exists(ruta_local):
        print(f"  -> Cargando BD vectorial desde '{ruta_local}'...")
        with open(ruta_local, 'rb') as f:
            return pickle.load(f)
    return []

def guardar_bd(bd, ruta_local):
    with open(ruta_local, 'wb') as f:
        pickle.dump(bd, f)

def extraer_documentos(rutas):
    docs = []
    for ruta in rutas:
        if not os.path.exists(ruta):
            print(f"  [WARN] RAG no encontrado: {os.path.basename(ruta)}")
            continue
        try:
            if ruta.lower().endswith('.pdf'):
                with open(ruta, 'rb') as f:
                    lector = PyPDF2.PdfReader(f)
                    for n, pagina in enumerate(lector.pages):
                        texto = pagina.extract_text() or ""
                        if texto.strip():
                            # chunking fino por página
                            nombre = f"{os.path.basename(ruta)}_p{n+1}"
                            docs.extend(chunk_texto(texto, nombre))
            else:
                with open(ruta, 'r', encoding='utf-8') as f:
                    texto = f.read()
                if texto.strip():
                    docs.extend(chunk_texto(texto, os.path.basename(ruta)))
        except Exception as e:
            print(f"  [ERROR] Leyendo {os.path.basename(ruta)}: {e}")
    return docs

def vectorizar_pendientes(bd, docs_extraidos):
    ya_procesados = {d["nombre"] for d in bd}
    pendientes = [d for d in docs_extraidos if d["nombre"] not in ya_procesados]
    total = len(pendientes)
    if total == 0:
        return bd

    print(f"\n[3/4] Vectorizando {total} chunks nuevos...")
    for i, doc in enumerate(pendientes):
        exito, intentos = False, 0
        while not exito and intentos < 5:
            try:
                resp = client.models.embed_content(model=MODEL_EMB, contents=doc["texto"])
                bd.append({
                    "nombre": doc["nombre"],
                    "texto":  doc["texto"],
                    "vector": resp.embeddings[0].values,
                })
                exito = True
                print(f"  [{i+1}/{total}] {doc['nombre']}")
                if (i + 1) % 10 == 0 or (i + 1) == total:
                    guardar_bd(bd, BD_LOCAL)
                    print("  [✓] Checkpoint guardado.")
            except Exception as e:
                if "429" in str(e):
                    intentos += 1
                    espera = 60 * intentos
                    print(f"  [429] Límite API. Pausando {espera}s (intento {intentos}/5)...")
                    time.sleep(espera)
                else:
                    print(f"  [ERROR] Vectorización: {e}")
                    break
        if not exito:
            guardar_bd(bd, BD_LOCAL)
            raise RuntimeError(
                f"API bloqueada tras 5 intentos en '{doc['nombre']}'. "
                "Progreso guardado. Reinicia el script más tarde."
            )
    return bd

# ── Construcción del system prompt ───────────────────────────────────────────

SYSTEM_PROMPT_TEMPLATE = """
# ROL
Eres un Ingeniero Senior de Telecomunicaciones especializado en 5G O-RAN.
Despliegas entornos con srsRAN, OAI y Open5GS sobre Docker.

# CONTEXTO DE PLANTILLAS BASE (CAG)
Las siguientes plantillas son tu referencia estructural OBLIGATORIA.
Úsalas como esqueleto. El bloque ru_sdr es [INMUTABLE]: cópialo exactamente.
{contexto_cag}

# JERARQUÍA DE REGLAS (mayor número = mayor prioridad en conflicto)

## REGLA 1 — Coherencia PLMN
MCC y MNC deben ser idénticos en gNB, UE (IMSI) y Core.
El usuario los especificará en su petición. Extráelos y aplícalos.

## REGLA 2 — Coherencia de frecuencias (3GPP TS 38.101)
Banda 3:  dl_arfcn ∈ [361000, 376000]
Banda 78: dl_arfcn ∈ [620000, 653333]
Banda 41: dl_arfcn ∈ [499200, 537999]
Si hay inconsistencia, NO generes archivos. Responde:
  VALIDATION_ERROR: ARFCN <x> no corresponde a Banda <y>

## REGLA 3 — Coherencia SCS
common_scs == ssb_scs. Sin excepciones.

## REGLA 4 — Puertos ZMQ cruzados
gNB(tx=A, rx=B) ↔ UE(tx=B, rx=A)

## REGLA 5 — bind_addr [PREVALECE SOBRE TODAS]
- YAML gNB standalone → bind_addr: <IP del contenedor gNB, la indicará el usuario>
- gnb_compose_config en docker-compose → bind_addr: 0.0.0.0
Justificación: en el contenedor la IP específica existe; el compose usa 0.0.0.0
porque el override se aplica antes del bind real.

## REGLA 6 — Bloque ru_sdr [INMUTABLE]
Copia ru_sdr EXACTAMENTE del CAG. No alteres srate, device_args ni device_driver.

## REGLA 7 — Coherencia IMSI y SUBSCRIBER_DB [CRÍTICA]

### 7a — Formato IMSI
- El IMSI tiene el formato: MCC (3 dígitos) + MNC (2 ó 3 dígitos) + MSIN (dígitos restantes hasta 15 en total)
- El IMSI debe ser idéntico en el bloque [usim] del UE y en el campo IMSI del SUBSCRIBER_DB del docker-compose.
- Ejemplo con MCC=001, MNC=01, MSIN=0000000001 → IMSI=001010000000001

### 7b — Formato SUBSCRIBER_DB [OBLIGATORIO]
El campo SUBSCRIBER_DB en el docker-compose DEBE seguir EXACTAMENTE este orden de campos:
  IMSI, K, tipo_opc, OPC, AMF, SQN, IP_estática
Donde:
  - IMSI:       El mismo que en el bloque [usim] del UE (15 dígitos).
  - K:          La clave de autenticación del usuario indicada en la petición (32 hex).
                Corresponde al campo 'k' del bloque [usim] del UE.
  - tipo_opc:   Siempre 'opc' (en minúsculas) para Milenage con OPc derivado.
  - OPC:        El operador cifrado indicado en la petición (32 hex).
                Corresponde al campo 'opc' del bloque [usim] del UE.
  - AMF:        Valor fijo '8000' salvo que el usuario indique otro.
  - SQN:        Valor fijo '9' (número de secuencia inicial) salvo que el usuario indique otro.
  - IP_estática: IP del UE dentro del rango UE_IP_BASE (ej: 10.45.1.2).

ADVERTENCIA CRÍTICA — orden de K y OPC:
  El error más frecuente es intercambiar K y OPC. Verifica siempre:
    Posición 2 del SUBSCRIBER_DB = K = campo 'k' del [usim] del UE
    Posición 4 del SUBSCRIBER_DB = OPC = campo 'opc' del [usim] del UE
  Si estos valores no coinciden exactamente con los del UE, el core
  rechazará el registro con 'Authentication failure (MAC failure)'.

Ejemplo correcto con los datos del usuario:
  Si el usuario indica k=AAAA... y opc=BBBB..., el SUBSCRIBER_DB debe ser:
  SUBSCRIBER_DB=<IMSI>,AAAA...,opc,BBBB...,8000,9,10.45.1.2
  Y en el UE:
  k   = AAAA...
  opc = BBBB...

# CHECKLIST MENTAL (verifica antes de escribir cualquier archivo)
[ ] PLMN idéntico en los 3 archivos
[ ] dl_arfcn dentro del rango de band configurada
[ ] common_scs == ssb_scs
[ ] Puertos ZMQ cruzados: gNB(tx=A,rx=B) ↔ UE(tx=B,rx=A)
[ ] bind_addr según REGLA 5 (standalone vs compose)
[ ] ru_sdr copiado sin modificar del CAG
[ ] IMSI idéntico en [usim] del UE y en SUBSCRIBER_DB (posición 1)
[ ] K del [usim] del UE == campo en posición 2 del SUBSCRIBER_DB
[ ] OPC del [usim] del UE == campo en posición 4 del SUBSCRIBER_DB
[ ] tipo_opc en posición 3 del SUBSCRIBER_DB es exactamente 'opc'
[ ] AMF en posición 5 del SUBSCRIBER_DB es '8000' (o el indicado por el usuario)
[ ] IP estática en posición 7 está dentro del rango UE_IP_BASE definido en el docker-compose
Si falla alguno → VALIDATION_ERROR: <descripción detallada del campo incorrecto>

# FORMATO DE SALIDA OBLIGATORIO
Sin markdown. Sin texto fuera de los bloques.

---START_GNB---
[YAML del gNB]
---END_GNB---

---START_UE---
[.conf del UE]
---END_UE---

---START_DOCKER---
[docker-compose.yml]
---END_DOCKER---

---START_NOTES---
[Máximo 10 líneas: decisiones tomadas, referenciando RAG o CAG]
---END_NOTES---
"""

# ── Búsqueda RAG ──────────────────────────────────────────────────────────────

def buscar_rag(pregunta, bd, top_k=TOP_K):
    emb = client.models.embed_content(
        model=MODEL_EMB, contents=pregunta
    ).embeddings[0].values
    ranked = sorted(bd, key=lambda d: sim_cos(emb, d["vector"]), reverse=True)
    return ranked[:top_k]

# ── Parseo y validación de la respuesta ──────────────────────────────────────

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

# ── Exportación ───────────────────────────────────────────────────────────────

def exportar(bloques, timestamp):
    os.makedirs(RUTAS_SALIDA["gnb"],    exist_ok=True)
    os.makedirs(RUTAS_SALIDA["ue"],     exist_ok=True)
    os.makedirs(RUTAS_SALIDA["docker"], exist_ok=True)
    os.makedirs(RUTAS_SALIDA["pdf"],    exist_ok=True)

    archivos = {
        os.path.join(RUTAS_SALIDA["gnb"],    f"gnb_zmq.yaml"):        bloques["gnb"],
        os.path.join(RUTAS_SALIDA["ue"],     f"ue_zmq.conf"):         bloques["ue"],
        os.path.join(RUTAS_SALIDA["docker"], f"docker-compose.yml"):  bloques["docker"],
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
    ruta_pdf = os.path.join(RUTAS_SALIDA["pdf"], f"despliegue_e2e_{timestamp}.pdf")
    pdf.output(ruta_pdf)
    print(f"  [✓] Reporte PDF: {ruta_pdf}")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("\n[1/4] Construyendo CAG (Memoria Estática)...")
    contexto_cag = cargar_cag(RUTAS_CAG)
    if not contexto_cag.strip():
        raise RuntimeError("CAG vacío: no se encontró ninguna plantilla base.")

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(contexto_cag=contexto_cag)
    config_rol = types.GenerateContentConfig(
        system_instruction=system_prompt,
        temperature=0.1
    )

    print("[2/4] Preparando RAG (Memoria Dinámica)...")
    bd = cargar_bd(BD_LOCAL)
    docs = extraer_documentos(RUTAS_RAG)
    bd   = vectorizar_pendientes(bd, docs)
    print(f"\n[4/4] Motor CAG+RAG listo. {len(bd)} chunks indexados.\n")

    while True:
        user_input = input("Tú: ").strip()
        if user_input.lower() in ("salir", "exit", "quit"):
            break
        if not user_input:
            continue

        print("  Buscando contexto relevante (RAG)...")
        top_docs = buscar_rag(user_input, bd)

        contexto_rag = "--- TEORÍA 3GPP RECUPERADA (RAG) ---\n"
        print("  Páginas seleccionadas:")
        for doc in top_docs:
            sim = sim_cos(
                client.models.embed_content(model=MODEL_EMB, contents=user_input).embeddings[0].values,
                doc["vector"]
            )
            print(f"    * {doc['nombre']} (relevancia: {sim:.4f})")
            contexto_rag += f"\n[Fuente: {doc['nombre']}]\n{doc['texto']}\n"

        prompt_final = (
            f"Petición del usuario:\n{user_input}\n\n"
            f"{contexto_rag}\n\n"
            "Genera ahora los tres archivos siguiendo estrictamente "
            "las reglas del system prompt."
        )

        print("  Generando configuraciones...")
        try:
            response = client.models.generate_content(
                model=MODEL_GEN,
                contents=prompt_final,
                config=config_rol,
            )
            bloques, error = parsear_respuesta(response.text)

            if error:
                print(f"\n  [!] {error}")
                continue

            timestamp = int(time.time())
            exportar(bloques, timestamp)

            if bloques.get("notes"):
                print("\n--- NOTAS DEL MODELO ---")
                print(bloques["notes"])

        except Exception as e:
            print(f"\n  [ERROR API] {e}")

if __name__ == "__main__":
    main()