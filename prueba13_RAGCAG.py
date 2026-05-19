from google import genai
from google.genai import types
import os
import numpy as np
import time
from fpdf import FPDF
import PyPDF2
import pickle

client = genai.Client()

model_gen = "gemini-2.5-flash"
model_emb = "gemini-embedding-001"  

def sim_cos(vec1, vec2):
    return np.dot(vec1, vec2)/(np.linalg.norm(vec1) * np.linalg.norm(vec2))

def chat_terminal():
    
    print("\n[1/4] Iniciando Arquitectura Hibrida: Construyendo CAG (Memoria Estatica)...")
    
    # --- 1. LISTA CAG: ARCHIVOS ESTRUCTURALES Y PLANTILLAS ---
    rutas_cag = [
        "/home/alejandroro/TFG_5G_LLM/CONFIGS/5gc-tls-sepp3-315-010.yaml.in",
        "/home/alejandroro/TFG_5G_LLM/CONFIGS/gnb-001-01-ue-001-01.yaml.in",
        "/home/alejandroro/TFG_5G_LLM/CONFIGS/gnb-001-01-ue-315-010.yaml.in",
        "/home/alejandroro/TFG_5G_LLM/CONFIGS/gnb-001-01-ue-999-70.yaml.in",
        "/home/alejandroro/TFG_5G_LLM/CONFIGS/gnb-315-010-ue-001-01.yaml.in",
        "/home/alejandroro/TFG_5G_LLM/CONFIGS/gnb-315-010-ue-315-010.yaml.in",
        "/home/alejandroro/TFG_5G_LLM/CONFIGS/gnb-315-010-ue-999-70.yaml.in",
        "/home/alejandroro/TFG_5G_LLM/CONFIGS/gnb-999-70-ue-001-01.yaml.in",
        "/home/alejandroro/TFG_5G_LLM/CONFIGS/gnb-999-70-ue-315-010.yaml.in",
        "/home/alejandroro/TFG_5G_LLM/CONFIGS/gnb-999-70-ue-999-70.yaml.in",
        "/home/alejandroro/TFG_5G_LLM/CONFIGS/gnb_rf_b210_fdd_srsUE.yml",
        "/home/alejandroro/TFG_5G_LLM/CONFIGS/docker-compose.yml",
        "/home/alejandroro/TFG_5G_LLM/CONFIGS/gnb_zmq.yaml",
        "/home/alejandroro/TFG_5G_LLM/CONFIGS/ue_zmq.conf"
    ]

    contexto_cag = ""
    for ruta in rutas_cag:
        if os.path.exists(ruta):
            with open(ruta, 'r', encoding='utf-8') as f:
                contexto_cag += f"\n--- PLANTILLA: {os.path.basename(ruta)} ---\n{f.read()}\n"
        else:
            print(f"  Advertencia: No se encontro el archivo CAG {os.path.basename(ruta)}")

    # INYECTAMOS EL CAG DIRECTAMENTE EN EL PROMPT DEL SISTEMA
    prompt_v2 = f"""
    # ROL
    Eres un Ingeniero de Telecomunicaciones Senior experto en arquitecturas 4G/5G O-RAN. 
    Tienes amplia experiencia desplegando entornos core y RAN utilizando tecnologías como srsRAN,
    OpenAirInterface (OAI) y Open5GS sobre entornos contenedorizados con Docker.
    
    # OBJETIVO
    Generar simultáneamente tres archivos de configuración válidos (gNB, UE, Docker).

    # CONOCIMIENTO BASE GLOBAL (CAG)
    Utiliza estrictamente la estructura de estas plantillas YAML que tienes en tu memoria base:
    {contexto_cag}

    # REGLAS ESTRICTAS DE COHERENCIA E2E
    - El MCC y MNC deben ser idénticos en el gNB, en el UE (IMSI) y en el Core.
    - Las direcciones IP deben mapearse correctamente entre los tres ficheros según las redes definidas.
    - Los puertos TCP de ZMQ del gNB deben cruzarse de forma inversa con los del UE.
    - Utiliza la teoría recuperada del estándar 3GPP (que el usuario te pasará como contexto) para fundamentar los valores técnicos de Slicing, QCI, etc.

    # FORMATO SALIDA YAML
    El archivo de configuración YAML, deberá seguir estrictamente la estructura que se indica en gnb_zmq.yaml

    # FORMATO SALIDA YML
    El archivo de configuración YML, deberá seguir estrictamente la esctructura que se indica en docker-compose.yml

    # FORMATO SALIDA CONF
    El archivo de configuración CONF, deberá seguir estrictamente la estructura que se indica en ue_zmq.conf """

    configuration_rol = types.GenerateContentConfig(
        system_instruction=prompt_v2,
        temperature=0.1
    )

    print("[2/4] Preparando Arquitectura RAG (Memoria Dinamica para PDFs)...")

    # --- 2. LISTA RAG: MANUALES PESADOS Y ESPECIFICACIONES 3GPP ---
    rutas_rag = [
        "/home/alejandroro/TFG_5G_LLM/CONFIGS/ts_123501v160600p.pdf"
    ]

    archivo_bd_local = "base_datos_3gpp.pkl"
    bd_vectorial = []

    # COMPROBACIÓN DE CACHÉ LOCAL (Para no volver a vectorizar el PDF de 400 págs)
    if os.path.exists(archivo_bd_local):
        print(f"  -> Cargando base de datos vectorial local desde '{archivo_bd_local}'...")
        with open(archivo_bd_local, 'rb') as f:
            bd_vectorial = pickle.load(f)
        print(f"  -> Carga completada en 0 segundos. {len(bd_vectorial)} páginas del 3GPP listas.")
        
    else:
        documentos_extraidos = []
        print("  -> Base de datos no encontrada. Extrayendo páginas del PDF del 3GPP...")
        for ruta in rutas_rag:
            if not os.path.exists(ruta):
                print(f"  No encontrado: {os.path.basename(ruta)}")
                continue
            
            try:
                with open(ruta, 'rb') as f:
                    lector_pdf = PyPDF2.PdfReader(f)
                    for num_pagina, pagina in enumerate(lector_pdf.pages):
                        texto_pagina = pagina.extract_text()
                        if texto_pagina and texto_pagina.strip():
                            documentos_extraidos.append({
                                "nombre": f"{os.path.basename(ruta)} - Pag {num_pagina + 1}",
                                "texto": texto_pagina
                            })
            except Exception as e:
                print(f" Error al leer el PDF {os.path.basename(ruta)}: {e}")

        total_docs = len(documentos_extraidos)
        print(f"\n[3/4] Vectorizando {total_docs} páginas. Pausa de 5s activa para evitar baneos de Google...")
        for i, doc in enumerate(documentos_extraidos):
            exito = False
            intentos = 0
            while not exito and intentos < 3:
                try:
                    respuesta_emb = client.models.embed_content(
                        model=model_emb,
                        contents=doc["texto"]
                    )
                    vector = respuesta_emb.embeddings[0].values
                    bd_vectorial.append({
                        "nombre": doc["nombre"],
                        "texto": doc["texto"],
                        "vector": vector
                    })
                    exito = True
                    print(f"  [{i+1}/{total_docs}] Vectorizado: {doc['nombre']}")
                    time.sleep(5) 
                except Exception as e:
                    if "429" in str(e):
                        intentos += 1
                        print(f"   Límite superado. Pausando 60s (Intento {intentos}/3)...")
                        time.sleep(60)
                    else:
                        print(f"   Error inesperado: {e}")
                        break
        
        # GUARDAR EN DISCO AL TERMINAR
        with open(archivo_bd_local, 'wb') as f:
            pickle.dump(bd_vectorial, f)
        print(f"\n  Base de datos '{archivo_bd_local}' creada con éxito.")

    print(f"\n[4/4] Motor Hibrido CAG+RAG listo.")

    while True:
        user_input = input("\nTú: ")
        if user_input.lower() == "salir":
            break

        print(" Buscando en el documento 3GPP (RAG)...")
        
        try:
            emb_pregunta = client.models.embed_content(
                model=model_emb,
                contents=user_input
            ).embeddings[0].values

            resultados_busqueda = []
            for doc in bd_vectorial:
                similitud = sim_cos(emb_pregunta, doc["vector"])
                resultados_busqueda.append((similitud, doc))

            resultados_busqueda.sort(key=lambda x: x[0], reverse=True)
            
            # Extraemos las 3 páginas del PDF que mejor responden a la petición
            top_3_documentos = resultados_busqueda[:3]
            
            contexto_recuperado = "--- TEORIA 3GPP RECUPERADA (RAG) ---\n"
            print("  -> Páginas seleccionadas para justificar esta configuración:")
            for similitud, doc in top_3_documentos:
                print(f"     * {doc['nombre']} (Relevancia: {similitud:.4f})")
                contexto_recuperado += f"\n[Página: {doc['nombre']}]\n{doc['texto']}\n"

            # El prompt final cruza la petición del usuario con la teoría del RAG
            prompt_rag_final = f"Petición del usuario: {user_input}\n\n{contexto_recuperado}"

            print(" Generando configuraciones E2E cruzando el 3GPP con las plantillas...")
            
            response = client.models.generate_content(
                model=model_gen,
                contents=prompt_rag_final,
                config=configuration_rol
            )
            
            raw_text = response.text
            timestamp = int(time.time())

            def extraer_bloque(texto, inicio, fin):
                try:
                    return texto.split(inicio)[1].split(fin)[0].strip()
                except IndexError:
                    return ""

            gnb_content = extraer_bloque(raw_text, "---START_GNB---", "---END_GNB---")
            ue_content = extraer_bloque(raw_text, "---START_UE---", "---END_UE---")
            docker_content = extraer_bloque(raw_text, "---START_DOCKER---", "---END_DOCKER---")

            if not gnb_content or not ue_content or not docker_content:
                print(" Error: El modelo no devolvió la estructura completa obligatoria. Reintentando...")
                continue

            print(f"\n Exportando archivos con ID: {timestamp}")

            with open(f"gnb_zmq_{timestamp}.yaml", "w", encoding="utf-8") as f:
                f.write(gnb_content)
            
            with open(f"ue_zmq_{timestamp}.conf", "w", encoding="utf-8") as f:
                f.write(ue_content)
            
            with open(f"docker-compose_{timestamp}.yml", "w", encoding="utf-8") as f:
                f.write(docker_content)

            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.set_font("Courier", size=8)

            def agregar_al_pdf(pdf, titulo, contenido):
                pdf.add_page()
                pdf.cell(0, 10, txt=titulo, ln=True, align='C')
                pdf.ln(5)
                for linea in contenido.split('\n'):
                    linea_segura = linea.encode('latin-1', 'replace').decode('latin-1')
                    pdf.cell(0, 4, txt=linea_segura, ln=True)

            agregar_al_pdf(pdf, f"=== CONFIGURACION GNB ({timestamp}) ===", gnb_content)
            agregar_al_pdf(pdf, f"=== CONFIGURACION UE ({timestamp}) ===", ue_content)
            agregar_al_pdf(pdf, f"=== DOCKER COMPOSE ({timestamp}) ===", docker_content)

            pdf.output(f"despliegue_e2e_{timestamp}.pdf")
            print(f" Reporte PDF y archivos generados con éxito.")
            
        except Exception as e:
            print(f"\nError de API: {e}")

if __name__ == "__main__":
    chat_terminal()