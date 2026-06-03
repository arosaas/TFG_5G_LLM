# -- ARQUITECTURA HIBRIDA CAG+RAG PARA CONFIGURACIONES 5G -- #
# Autor: Alejandro R. Sarabia
# Fecha 06/2026

import time
from google import genai
from google.genai import types

import configuraciones
from generar_configuraciones import parsear_respuesta, exportar
import modulos_ia
from utilidades import sim_cos

def main():
    print("Iniciando herramienta de configuración 5G...")

    client = genai.Client(api_key=configuraciones.API_KEY)

    print("\n[1/4] Construyendo CAG (Memoria Estática)...")
    cache = modulos_ia.cargar_cag(configuraciones.RUTAS_CAG, client, configuraciones.MODEL_GEN)
    

    print("[2/4] Preparando RAG (Memoria Dinámica)...")
    bd = modulos_ia.cargar_bd(configuraciones.BD_LOCAL)
    docs = modulos_ia.extraer_documentos(configuraciones.RUTAS_RAG)
    bd   = modulos_ia.vectorizar_pendientes(bd, docs, client)
    print(f"\n[4/4] Motor CAG+RAG listo. {len(bd)} chunks indexados.\n")


    config_generation = types.GenerateContentConfig(
        temperature=0.1,
        cached_content=cache.name
    )

    while True:
        user_input = input("Tú: ").strip()
        if user_input.lower() in ("salir", "exit", "quit"):
            break
        if not user_input:
            continue

        print("  Buscando contexto relevante (RAG)...")
        top_docs = modulos_ia.buscar_rag(user_input, bd)

        contexto_rag = "--- TEORÍA RECUPERADA (RAG) ---\n"
        print("  Páginas seleccionadas:")
        for doc in top_docs:
            sim = sim_cos(
                client.models.embed_content(model=configuraciones.MODEL_EMB, contents=user_input).embeddings[0].values,
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
                model=configuraciones.MODEL_GEN,
                contents=prompt_final,
                config=config_generation,
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