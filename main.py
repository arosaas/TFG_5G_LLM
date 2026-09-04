# -- ARQUITECTURA HIBRIDA CAG+RAG PARA CONFIGURACIONES 5G -- #
# Autor: Alejandro R. Sarabia
# Fecha 06/2026

import time
import logging
from google import genai
from google.genai import types

import configuraciones
from generar_configuraciones import parsear_respuesta, exportar
import modulos_ia
from utilidades import sim_cos
import datetime
from llm_utils import get_llm_provider, get_model_name

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


def main():
    start = datetime.datetime.now()
    logger.info("Starting 5G configuration tool")
    print("Iniciando herramienta de configuración 5G...")

    logger.info("Initializing LLM provider")
    llm_provider = get_llm_provider()
    model_gen = get_model_name("gen")
    model_emb = get_model_name("emb")

    logger.info("Step 1/4: Building CAG (Static Memory)")
    print("\n[1/4] Construyendo CAG (Memoria Estática)...")
    cache = modulos_ia.cargar_cag(configuraciones.RUTAS_CAG, llm_provider, model_gen)


    logger.info("Step 2/4: Preparing RAG (Dynamic Memory)")
    print("[2/4] Preparando RAG (Memoria Dinámica)...")
    bd = modulos_ia.cargar_bd(configuraciones.BD_LOCAL)
    docs = modulos_ia.extraer_documentos(configuraciones.RUTAS_RAG)
    bd   = modulos_ia.vectorizar_pendientes(bd, docs, llm_provider)
    logger.info(f"RAG preparation complete: {len(bd)} chunks indexed")
    print(f"\n[4/4] Motor CAG+RAG listo. {len(bd)} chunks indexados.\n")


    config_generation = types.GenerateContentConfig(
        temperature=0.1,
        cached_content=cache.name
    )

    logger.info("Entering main interaction loop")
    while True:
        user_input = input("Tú: ").strip()
        if user_input.lower() in ("salir", "exit", "quit"):
            logger.info("User initiated exit")
            break
        if not user_input:
            continue

        logger.info(f"Processing user query: '{user_input[:50]}...'")
        print("  Buscando contexto relevante (RAG)...")
        top_docs = modulos_ia.buscar_rag(user_input, bd, llm_provider)

        contexto_rag = "--- TEORÍA RECUPERADA (RAG) ---\n"
        print("  Páginas seleccionadas:")
        for doc in top_docs:
            sim = sim_cos(
                llm_provider.embed_content(model=model_emb, contents=user_input).embeddings[0].values,
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

        logger.info("Generating configurations with LLM")
        print("  Generando configuraciones...")
        try:
            response = llm_provider.generate_content(
                model=model_gen,
                contents=prompt_final,
                config=config_generation,
            )
            bloques, error = parsear_respuesta(response.text)

            if error:
                logger.warning(f"Configuration generation failed: {error}")
                print(f"\n  [!] {error}")
                continue

            timestamp = int(time.time())
            logger.info(f"Exporting generated configurations with timestamp {timestamp}")
            exportar(bloques, timestamp)

            if bloques.get("notes"):
                logger.info("Model returned notes")
                print("\n--- NOTAS DEL MODELO ---")
                print(bloques["notes"])
                end = datetime.datetime.now()
                total_time = (end - start).total_seconds()
                logger.info(f"Total execution time: {total_time:.2f} seconds")
                print(f"\nTiempo total desde inicio: {total_time:.2f} segundos")


        except Exception as e:
            logger.error(f"Error during configuration generation: {e}")
            print(f"\n  [ERROR] {e}")

if __name__ == "__main__":
    main()