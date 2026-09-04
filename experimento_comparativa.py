# -- ARQUITECTURA HIBRIDA CAG+RAG PARA CONFIGURACIONES 5G -- #
# Autor: Alejandro R. Sarabia
# Fecha 06/2026

"""
Automatiza la comparativa "LLM sin RAG/CAG" vs "Sistema propuesto (RAG/CAG)"
repitiendo EXACTAMENTE EL MISMO PROMPT N veces en cada método, para poder
construir una estadística real en lugar de una única ejecución puntual.

La configuración manual NO se automatiza aquí (no tiene sentido repetirla
15-20 veces a mano); solo se automatizan los dos métodos basados en LLM.

Uso:
    python3 experimento_comparativa.py --metodo sin_rag_cag
    python3 experimento_comparativa.py --metodo sistema_propuesto

Genera un CSV (resultados_comparativa.csv) con una fila por ejecución.

IMPORTANTE:
- El método "sin_rag_cag" reproduce el enfoque de tu prueba1.py: se llama
  al modelo directamente, sin System Prompt, sin RAG y sin CAG. Como no
  hay delimitadores ---START_GNB---, etc. (esos los define tu propio
  System Prompt), la función parsear_respuesta() casi con toda seguridad
  no encontrará estructura, lo cual es precisamente el comportamiento que
  ya documentaste en el Capítulo 7. La respuesta completa del modelo se
  guarda en la columna 'notas' del CSV para que puedas revisarla a mano
  y clasificar manualmente qué tipo de error concreto es cada fallo
  (formato, coherencia, alucinación...), ya que sin la estructura de
  bloques no hay forma de automatizar esa clasificación fina.
- El método "sistema_propuesto" reutiliza tus propios módulos
  (modulos_ia, generar_configuraciones, utilidades) tal cual están en
  el repositorio, con temperatura 0.1 y top-k=5 (los valores elegidos
  en el proyecto).
- Este script no inventa ni simula resultados: cada fila del CSV
  corresponde a una llamada real a la API.
"""

import argparse
import csv
import time
from pathlib import Path

from google import genai
from google.genai import types

import configuraciones
import modulos_ia
from generar_configuraciones import parsear_respuesta, exportar

N_REPETICIONES = 20

PROMPT = (
    "Configura un entorno O-RAN E2E completo para un caso de comunicacion terrestre "
    "estandar. Busca en la base de datos RAG el valor SST estandarizado correspondiente "
    "a eMBB, requerido para aplicaciones de seguridad vial con latencias sub-10ms y "
    "aplicalo al bloque tai_slice_support_list del gNB anadiendo un comentario YAML que "
    "indique la seccion o tabla del estandar de la que has extraido el valor. Configura "
    "la red PLMN con MCC 001, MNC 01 y TAC 7. Usa la Banda 3 con dl_arfcn 368500, ancho "
    "de banda de 10 MHz y SCS de 15 kHZ. Estos parametros son obligatorios porque deben "
    "ser compatibles con la tasa de muestreo de 11.52 Mbps impuesta por el entorno ZMQ. "
    "Para el enlace de radio virtual ZMQ, cruza los puertos 2000 y 2001 entre el gNB y "
    "el UE. La IP del contenedor gNB sera 10.53.1.1 y la del core de Open5GS sera "
    "10.53.1.2, que coincidira con la direccion AMF. El UE debe utilizar el algoritmo "
    "Milenage con los siguientes parametros de autenticacion: IMSI: 001010000000001, K: "
    "00aabbccddeeff112233445566778899, OPC:112233445566778899aabbccddeeff00. Activa las "
    "metricas de RLC y del scheduler DU con un periodo de reporte de 400 ms para "
    "monitorizar la latencia del plano de usuario en tiempo real. Habilita tambien las "
    "capturas PCAP de NGAP"
)

CSV_SALIDA = Path("resultados_comparativa.csv")
CAMPOS_CSV = [
    "metodo", "repeticion", "tiempo_s",
    "exito", "error_sintactico", "error_coherencia", "notas",
]


def registrar_fila(fila: dict):
    existe = CSV_SALIDA.exists()
    with open(CSV_SALIDA, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CAMPOS_CSV)
        if not existe:
            writer.writeheader()
        writer.writerow(fila)


def ejecutar_sin_rag_cag(client, repeticion):
    """Reproduce el enfoque de prueba1.py: modelo en bruto, sin System Prompt/RAG/CAG."""
    inicio = time.time()
    fila = {
        "metodo": "sin_rag_cag", "repeticion": repeticion, "tiempo_s": None,
        "exito": False, "error_sintactico": False, "error_coherencia": False, "notas": "",
    }
    try:
        # Se pide directamente al modelo, en lenguaje natural, que genere los
        # tres ficheros, sin ninguna plantilla ni contexto adicional, igual
        # que se describe en el Capítulo 7 para este escenario de referencia.
        prompt_natural = (
            f"{PROMPT}\n\nGenera los tres archivos de configuración necesarios "
            "(gNB, UE y docker-compose)."
        )
        response = client.models.generate_content(
            model=configuraciones.MODEL_GEN,
            contents=prompt_natural,
        )
        fila["tiempo_s"] = round(time.time() - inicio, 2)

        bloques, error = parsear_respuesta(response.text)
        if error or bloques is None:
            fila["error_sintactico"] = True
            fila["notas"] = response.text[:2000]  # guardamos la respuesta cruda para revisión manual
        else:
            fila["exito"] = True
            fila["notas"] = "Estructura detectada (revisar coherencia manualmente)"

    except Exception as e:
        fila["tiempo_s"] = round(time.time() - inicio, 2)
        fila["error_coherencia"] = True
        fila["notas"] = f"[ERROR API] {e}"

    registrar_fila(fila)
    print(f"  [sin_rag_cag] repetición {repeticion}: "
          f"{'OK (revisar a mano)' if fila['exito'] else 'SIN ESTRUCTURA'} ({fila['tiempo_s']}s)")


def ejecutar_sistema_propuesto(client, cache, bd, repeticion):
    inicio = time.time()
    fila = {
        "metodo": "sistema_propuesto", "repeticion": repeticion, "tiempo_s": None,
        "exito": False, "error_sintactico": False, "error_coherencia": False, "notas": "",
    }
    try:
        top_docs = modulos_ia.buscar_rag(PROMPT, bd, client, top_k=configuraciones.TOP_K)
        contexto_rag = "--- TEORÍA RECUPERADA (RAG) ---\n"
        for doc in top_docs:
            contexto_rag += f"\n[Fuente: {doc['nombre']}]\n{doc['texto']}\n"

        prompt_final = (
            f"Petición del usuario:\n{PROMPT}\n\n{contexto_rag}\n\n"
            "Genera ahora los tres archivos siguiendo estrictamente las reglas del system prompt."
        )

        config_generation = types.GenerateContentConfig(
            temperature=0.1,
            cached_content=cache.name,
        )

        response = client.models.generate_content(
            model=configuraciones.MODEL_GEN,
            contents=prompt_final,
            config=config_generation,
        )

        bloques, error = parsear_respuesta(response.text)
        fila["tiempo_s"] = round(time.time() - inicio, 2)

        if error:
            fila["error_sintactico"] = True
            fila["notas"] = error
        else:
            fila["exito"] = True
            exportar(bloques, int(time.time()))
            fila["notas"] = "Exportado correctamente (revisar coherencia manualmente si procede)"

    except Exception as e:
        fila["tiempo_s"] = round(time.time() - inicio, 2)
        fila["error_coherencia"] = True
        fila["notas"] = f"[ERROR API] {e}"

    registrar_fila(fila)
    print(f"  [sistema_propuesto] repetición {repeticion}: "
          f"{'OK' if fila['exito'] else 'FALLO'} ({fila['tiempo_s']}s)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--metodo", choices=["sin_rag_cag", "sistema_propuesto"], required=True)
    parser.add_argument("--n", type=int, default=N_REPETICIONES,
                         help="Número de repeticiones (por defecto 20)")
    args = parser.parse_args()

    client = genai.Client(api_key=configuraciones.API_KEY)

    if args.metodo == "sin_rag_cag":
        for i in range(1, args.n + 1):
            ejecutar_sin_rag_cag(client, repeticion=i)
    else:
        cache = modulos_ia.cargar_cag(configuraciones.RUTAS_CAG, client, configuraciones.MODEL_GEN)
        bd = modulos_ia.cargar_bd(configuraciones.BD_LOCAL)
        for i in range(1, args.n + 1):
            ejecutar_sistema_propuesto(client, cache, bd, repeticion=i)

    print(f"\nResultados guardados en {CSV_SALIDA.resolve()}")


if __name__ == "__main__":
    main()