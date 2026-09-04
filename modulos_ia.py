# -- ARQUITECTURA HIBRIDA CAG+RAG PARA CONFIGURACIONES 5G -- #
# Autor: Alejandro R. Sarabia
# Fecha 06/2026

import os
import time
import pickle
import PyPDF2
from google.genai import types
from utilidades import sim_cos, extraer_bloque, chunk_texto
import configuraciones 
from generar_prompt import SYSTEM_PROMPT_TEMPLATE

## -- Carga del CAG -- ##

def cargar_cag(rutas, client, modelo):
    """
    Lee las plantillas locales, construye el prompt del sistema y
    crea un Context Cache real en los servidores de Google (CAG).
    """

    contexto_local = ""
    for ruta in rutas:
        if os.path.exists(ruta):
            with open(ruta, 'r', encoding='utf-8') as f:
                contexto_local += f"\n--- PLANTILLA: {os.path.basename(ruta)} ---\n{f.read()}\n"
        else:
            print(f"  [WARN] Plantilla no encontrada: {os.path.basename(ruta)}")

    if not contexto_local.strip():
        raise RuntimeError("Error: No se encontró ninguna plantilla base para el CAG.")

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(contexto_cag=contexto_local)


    print("  -> Subiendo el Contexto Estático (CAG) a la API de Google...")
    cache = client.caches.create(
        model=modelo,
        config=types.CreateCachedContentConfig(
            system_instruction=system_prompt,
            contents=[
                types.Content(
                    role="user", 
                    parts=[types.Part.from_text(text="Inicializando contexto CAG base.")]
                )
            ],
            ttl="7200s" 
        )
    )
    print(f"  [✓] Caché creada con éxito en la nube: {cache.name}")
    
    return cache

## -- Funciones para RAG -- ##

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

def vectorizar_pendientes(bd, docs_extraidos, client):
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
                resp = client.models.embed_content(model=configuraciones.MODEL_EMB, contents=doc["texto"])
                bd.append({
                    "nombre": doc["nombre"],
                    "texto":  doc["texto"],
                    "vector": resp.embeddings[0].values,
                })
                exito = True
                print(f"  [{i+1}/{total}] {doc['nombre']}")
                if (i + 1) % 10 == 0 or (i + 1) == total:
                    guardar_bd(bd, configuraciones.BD_LOCAL)
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
            guardar_bd(bd, configuraciones.BD_LOCAL)
            raise RuntimeError(
                f"API bloqueada tras 5 intentos en '{doc['nombre']}'. "
                "Progreso guardado. Reinicia el script más tarde."
            )
    return bd

## -- Busqueda RAG -- ##

def buscar_rag(pregunta, bd, client, top_k=configuraciones.TOP_K):
    emb = client.models.embed_content(
        model=configuraciones.MODEL_EMB, contents=pregunta
    ).embeddings[0].values
    ranked = sorted(bd, key=lambda d: sim_cos(emb, d["vector"]), reverse=True)
    return ranked[:top_k]