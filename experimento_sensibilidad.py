# -- ARQUITECTURA HIBRIDA CAG+RAG PARA CONFIGURACIONES 5G -- #
# Autor: Alejandro R. Sarabia
# Fecha 06/2026

"""
Script de automatización para las pruebas de sensibilidad (temperatura y top-k).

Uso previsto:
    1. Rellena la lista PROMPTS con tus 15-20 variantes (o carga desde el .md que te generé).
    2. Ajusta TEMPERATURAS o TOP_KS según la prueba que quieras correr.
    3. Ejecuta: python3 experimento_sensibilidad.py --modo temperatura
       o bien:  python3 experimento_sensibilidad.py --modo topk

    Genera un CSV con una fila por ejecución, listo para graficar con
    graficar_resultados.py (te lo doy en el siguiente paso).

IMPORTANTE: este script reutiliza tus módulos tal cual están en el repo.
No inventa resultados: cada fila del CSV corresponde a una llamada real
a la API que tú ejecutas. Si una llamada falla o tarda demasiado, el
script lo registra como error en lugar de simularlo.
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
from utilidades import sim_cos

PROMPTS = [
    "Realiza un despliegue de srsRAN en Banda 78 utilizando 20 MHz de ancho de banda. "
    "El suscriptor tiene IMSI 214010000000001 y clave K 00112233445566778899aabbccddeeff. "
    "Utiliza el OPC del template.",

    "Despliega un entorno srsRAN en la Banda 78 con 20 MHz de ancho de banda. "
    "El IMSI del suscriptor es 214010000000002 y su clave K es 11223344556677889900aabbccddeeff. "
    "Usa el OPC de la plantilla base.",

    "Necesito configurar srsRAN sobre Banda 78 con un ancho de banda de 20 MHz. "
    "IMSI: 214010000000003. K: 223344556677889900aabbccddeeff11. "
    "El OPC debe tomarse del template.",

    "Configura el entorno con srsRAN en Banda 78, ancho de banda 20 MHz. "
    "Suscriptor con IMSI 214010000000004 y K 3344556677889900aabbccddeeff1122. "
    "Emplea el OPC ya definido en la plantilla.",

    "Quiero un despliegue srsRAN en Banda 78 a 20 MHz de ancho de banda. "
    "IMSI 214010000000005, K 44556677889900aabbccddeeff112233. "
    "El OPC, el de la plantilla.",

    "Levanta srsRAN en Banda 78 con 20 MHz. "
    "El suscriptor tiene IMSI 214010000000006 y K 556677889900aabbccddeeff1122334. "
    "Utiliza el OPC del template base.",

    "Despliegue de srsRAN requerido: Banda 78, 20 MHz de ancho de banda. "
    "IMSI: 214010000000007. K: 6677889900aabbccddeeff11223344556. "
    "OPC: el de la plantilla.",

    "Configura srsRAN para operar en Banda 78 con 20 MHz. "
    "IMSI del suscriptor: 214010000000008. Clave K: 7788990 0aabbccddeeff1122334455. "
    "Usa el OPC de plantilla.",

    "Realiza el despliegue en Banda 78, ancho de banda de 20 MHz, usando srsRAN. "
    "Suscriptor IMSI 214010000000009, K 8899 00aabbccddeeff112233445566. "
    "OPC de la plantilla.",

    "Necesito srsRAN desplegado en Banda 78 con 20 MHz de ancho de banda. "
    "IMSI 214010000000010, K 9900aabbccddeeff11223344556677. "
    "Utiliza el OPC del template.",

    "Pon en marcha srsRAN en Banda 78 con 20 MHz. "
    "El suscriptor: IMSI 214010000000011, K 00aabbccddeeff1122334455667788. "
    "El OPC, tómalo de la plantilla.",

    "Despliega srsRAN sobre Banda 78, 20 MHz de ancho de banda. "
    "IMSI: 214010000000012. K: 0aabbccddeeff112233445566778899. "
    "OPC: el definido en la plantilla base.",

    "Configura un entorno srsRAN en Banda 78 con 20 MHz. "
    "Suscriptor con IMSI 214010000000013 y K aabbccddeeff11223344556677889900. "
    "Usa el OPC de la plantilla.",

    "Despliegue solicitado: srsRAN, Banda 78, 20 MHz de ancho de banda. "
    "IMSI 214010000000014, K abbccddeeff112233445566778899aa. "
    "OPC de plantilla.",

    "Realiza un despliegue srsRAN en Banda 78 con 20 MHz de ancho de banda. "
    "IMSI: 214010000000015. K: bbccddeeff112233445566778899aab. "
    "El OPC debe ser el de la plantilla.",

    "Necesito configurar srsRAN en Banda 78, 20 MHz. "
    "El suscriptor tiene IMSI 214010000000016 y K bccddeeff112233445566778899aabb. "
    "Utiliza el OPC de plantilla.",

    "Despliega srsRAN operando en Banda 78 con 20 MHz de ancho de banda. "
    "IMSI 214010000000017, K ccddeeff112233445566778899aabbc. "
    "OPC: el de la plantilla.",

    "Configura el sistema srsRAN para Banda 78 con 20 MHz. "
    "Suscriptor IMSI 214010000000018, K cddeeff112233445566778899aabbcc. "
    "Emplea el OPC del template.",

    "Pon a funcionar srsRAN en Banda 78 con 20 MHz de ancho de banda. "
    "IMSI: 214010000000019. K: ddeeff112233445566778899aabbccd. "
    "OPC de la plantilla base.",

    "Realiza el despliegue de srsRAN en Banda 78, ancho de banda 20 MHz. "
    "El suscriptor tiene IMSI 214010000000020 y K deeff112233445566778899aabbccdd. "
    "Usa el OPC ya presente en la plantilla.",
]

TEMPERATURAS = [0.6, 0.7]
TOP_KS = [2, 5, 10]

CSV_SALIDA = Path("resultados_sensibilidad.csv")
CAMPOS_CSV = [
    "modo", "parametro_valor", "prompt_id", "tiempo_s",
    "exito", "error_sintactico", "error_coherencia",
    "reglas_incumplidas", "notas",
]


def registrar_fila(fila: dict):
    existe = CSV_SALIDA.exists()
    with open(CSV_SALIDA, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CAMPOS_CSV)
        if not existe:
            writer.writeheader()
        writer.writerow(fila)


def ejecutar_una_vez(client, cache, bd, prompt_id, prompt_texto, temperatura, top_k, modo, parametro_valor):
    inicio = time.time()
    fila = {
        "modo": modo,
        "parametro_valor": parametro_valor,
        "prompt_id": prompt_id,
        "tiempo_s": None,
        "exito": False,
        "error_sintactico": False,
        "error_coherencia": False,
        "reglas_incumplidas": "",
        "notas": "",
    }

    try:
        top_docs = modulos_ia.buscar_rag(prompt_texto, bd, client, top_k=top_k)
        contexto_rag = "--- TEORÍA RECUPERADA (RAG) ---\n"
        for doc in top_docs:
            contexto_rag += f"\n[Fuente: {doc['nombre']}]\n{doc['texto']}\n"

        prompt_final = (
            f"Petición del usuario:\n{prompt_texto}\n\n{contexto_rag}\n\n"
            "Genera ahora los tres archivos siguiendo estrictamente las reglas del system prompt."
        )

        config_generation = types.GenerateContentConfig(
            temperature=temperatura,
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
            # -- AQUI ES DONDE TU DEBES REVISAR MANUALMENTE --
            # el resultado generado (bloques["gnb"], bloques["ue"], bloques["docker"])
            # y anotar en 'reglas_incumplidas' cuáles de las 8 reglas del System Prompt
            # no se cumplieron, tal y como haces en las Tablas 7.x del capítulo.
            # Este script NO puede evaluar coherencia semántica automáticamente.
            exportar(bloques, int(time.time()))

    except Exception as e:
        fila["tiempo_s"] = round(time.time() - inicio, 2)
        fila["error_coherencia"] = True
        fila["notas"] = f"[ERROR API] {e}"

    registrar_fila(fila)
    print(f"  [{modo}={parametro_valor}] prompt {prompt_id}: "
          f"{'OK' if fila['exito'] else 'FALLO'} ({fila['tiempo_s']}s)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--modo", choices=["temperatura", "topk"], required=True)
    args = parser.parse_args()

    if not PROMPTS:
        raise RuntimeError(
            "Rellena la lista PROMPTS con tus variantes antes de ejecutar el script."
        )

    client = genai.Client(api_key=configuraciones.API_KEY)
    cache = modulos_ia.cargar_cag(configuraciones.RUTAS_CAG, client, configuraciones.MODEL_GEN)
    bd = modulos_ia.cargar_bd(configuraciones.BD_LOCAL)

    if args.modo == "temperatura":
        for temp in TEMPERATURAS:
            for i, prompt in enumerate(PROMPTS, start=1):
                ejecutar_una_vez(
                    client, cache, bd, prompt_id=i, prompt_texto=prompt,
                    temperatura=temp, top_k=configuraciones.TOP_K,
                    modo="temperatura", parametro_valor=temp,
                )
    else:
        for k in TOP_KS:
            for i, prompt in enumerate(PROMPTS, start=1):
                ejecutar_una_vez(
                    client, cache, bd, prompt_id=i, prompt_texto=prompt,
                    temperatura=0.1, top_k=k,
                    modo="topk", parametro_valor=k,
                )

    print(f"\nResultados guardados en {CSV_SALIDA.resolve()}")


if __name__ == "__main__":
    main()