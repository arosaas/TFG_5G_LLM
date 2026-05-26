import os
import time
import pickle
import PyPDF2
from google import genai

# Configura tu cliente de Gemini
client = genai.Client()
model_emb = "gemini-embedding-001"

rutas_rag = [
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/ts_123501v160600p.pdf",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/O-RAN.WG1.TR.Use-Cases-Analysis-Report-R005-v19.00-1.pdf",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/ejemplos_configuraciones_5g.pdf"
]

archivo_bd_local = "/home/alejandroro/TFG_5G_LLM/base_datos_5g_tfg.pkl"
bd_vectorial = []

# Cargar progreso si existe
if os.path.exists(archivo_bd_local):
    print(f"Cargando progreso previo de {archivo_bd_local}...")
    with open(archivo_bd_local, 'rb') as f:
        bd_vectorial = pickle.load(f)

# Extraer texto de los PDFs
documentos_extraidos = []
print("Extrayendo texto de los PDFs...")
for ruta in rutas_rag:
    if os.path.exists(ruta):
        with open(ruta, 'rb') as f:
            lector_pdf = PyPDF2.PdfReader(f)
            for num_pagina, pagina in enumerate(lector_pdf.pages):
                texto = pagina.extract_text()
                if texto and texto.strip():
                    documentos_extraidos.append({
                        "nombre": f"{os.path.basename(ruta)} - Pag {num_pagina + 1}",
                        "texto": texto
                    })

# Filtrar lo que ya está procesado
procesados = {doc["nombre"] for doc in bd_vectorial}
pendientes = [doc for doc in documentos_extraidos if doc["nombre"] not in procesados]

total = len(pendientes)
if total == 0:
    print("¡La base de datos ya está 100% completa!")
    exit(0)

print(f"Faltan {total} páginas por vectorizar. Empezando...")

# Vectorizar con manejo de cuota
for i, doc in enumerate(pendientes):
    intentos = 0
    exito = False
    while not exito and intentos < 5:
        try:
            respuesta_emb = client.models.embed_content(model=model_emb, contents=doc["texto"])
            bd_vectorial.append({
                "nombre": doc["nombre"],
                "texto": doc["texto"],
                "vector": respuesta_emb.embeddings[0].values
            })
            exito = True
            print(f"[{i+1}/{total}] OK: {doc['nombre']}")
            
            # Guardado progresivo
            if (i + 1) % 10 == 0 or (i + 1) == total:
                with open(archivo_bd_local, 'wb') as f:
                    pickle.dump(bd_vectorial, f)
                print(" -> Checkpoint guardado.")
                
            time.sleep(4) # Pausa normal
            
        except Exception as e:
            if "429" in str(e):
                intentos += 1
                espera = 60 * intentos
                print(f"Límite API. Pausa de {espera}s (Intento {intentos}/5)...")
                time.sleep(espera)
            else:
                print(f"Error fatal: {e}")
                break

print("\n¡PROCESO TERMINADO! Base de datos lista para usar.")