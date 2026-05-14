from google import genai
from google.genai import types
import os
import numpy as np
import time
from fpdf import FPDF
import PyPDF2

client = genai.Client()

model_gen = "gemini-2.5-flash"
model_emb = "gemini-embedding-001"

def sim_cos(vec1, vec2):
    return np.dot(vec1, vec2)/(np.linalg.norm(vec1) * np.linalg.norm(vec2))

def chat_terminal():
    
    prompt_v2 = """
    # ROL
    Eres un Ingeniero de Telecomunicaciones Senior experto en 
    arquitecturas 4G/5G O-RAN. Tienes amplia experiencia desplegando 
    entornos core y RAN utilizando tecnologias como srsRAN,
    OpenAirInterface (OAI) y Open5GS.
    
    # OBJETIVO
    Generar archivos de configuracion validos y listos para produccion. 
    El usuario te proporcionara su peticion, y el sistema adjuntara 
    automaticamente los fragmentos de configuracion o extractos de manuales tecnicos mas relevantes 
    (RAG) para que los uses como contexto.
    
    # REGLAS ESTRICTAS DE GENERACION
    1. EXTRACCION: Analiza el contexto recuperado (Documentos recuperados) 
    para encontrar las variables necesarias (IPs, MCC, MNC, etc.) o instrucciones tecnicas.
    2. SUSTITUCION: Sustituye las etiquetas (< >) de la plantilla base 
    con los valores extraidos.
    3. CERO ALUCINACIONES: Si falta un dato, usa un valor estandar 
    de Open5GS y añade `# REVISAR: Valor asumido por falta de datos`.
    4. FORMATO DE SALIDA: Devuelve UNICAMENTE el codigo YAML. No añadas texto introductorio.
    
    # PLANTILLA BASE OBLIGATORIA
    (Se asume la estructura Open5GS estandar definida previamente)

    
    """

    configuration_rol = types.GenerateContentConfig(
        system_instruction=prompt_v2,
        temperature=0.2
    )

    rutas_archivos = [
        "/home/alejandroro/Escritorio/TFG/CONFIGS/5gc-tls-sepp3-315-010.yaml.in",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/gnb-001-01-ue-001-01.yaml.in",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/gnb-001-01-ue-315-010.yaml.in",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/gnb-001-01-ue-999-70.yaml.in",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/gnb-315-010-ue-001-01.yaml.in",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/gnb-315-010-ue-315-010.yaml.in",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/gnb-315-010-ue-999-70.yaml.in",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/gnb-999-70-ue-001-01.yaml.in",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/gnb-999-70-ue-315-010.yaml.in",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/gnb-999-70-ue-999-70.yaml.in",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/gnb_rf_b210_fdd_srsUE.yml"
        "/home/alejandroro/Escritorio/TFG/CONFIGS/Comparative E2E Performance Analysis of O-RAN_0ADesigns in a 5G Standalone Testbed.pdf"
        "/home/alejandroro/Escritorio/TFG/CONFIGS/AI-Driven_Zero_Touch_Network_and_Service_Management_in_5G_and_Beyond_Challenges_and_Research_Directions.pdf"
        "/home/alejandroro/Escritorio/TFG/CONFIGS/Control_Plane_Performance_Benchmarking_and_Feature_Analysis_of_Popular_Open-Source_5G_Core_Networks_OpenAirInterface_Open5GS_and_free5GC.pdf"
    ]

    bd_vectorial = []
    documentos_extraidos = []

    print("\nFase 1: Extrayendo texto de los archivos (YAML y PDF)...")
    for ruta in rutas_archivos:
        if not os.path.exists(ruta):
            print(f"No encontrado: {os.path.basename(ruta)}")
            continue

        if ruta.lower().endswith('.pdf'):
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
                            print(f"  Extraido: {os.path.basename(ruta)} - Pag {num_pagina + 1}")
            except Exception as e:
                print(f"Error al leer el PDF {os.path.basename(ruta)}: {e}")
        else:
            with open(ruta, 'r', encoding='utf-8') as f:
                contenido_texto = f.read()
            documentos_extraidos.append({
                "nombre": os.path.basename(ruta),
                "texto": contenido_texto
            })

    print("\nFase 2: Vectorizando archivos. Esto tomara tiempo para respetar los limites de la API...")
    for doc in documentos_extraidos:
        exito = False
        intentos = 0
        
        while not exito and intentos < 4:
            try:
                respuesta_emb = client.models.embed_content(
                    model=model_emb,
                    contents=doc["texto"]
                )
                vector = respuesta_emb.embeddings[0].values
                exito = True
                
            except Exception as e:
                if "429" in str(e):
                    intentos += 1
                    print(f"  Limite alcanzado con {doc['nombre']}. Pausa de 15 segundos (Intento {intentos}/3)...")
                    time.sleep(15) 
                else:
                    print(f"  Error inesperado con {doc['nombre']}: {e}")
                    break
        
        if exito:
            bd_vectorial.append({
                "nombre": doc["nombre"],
                "texto": doc["texto"],
                "vector": vector
            })
            print(f"Vectorizado: {doc['nombre']}")
            time.sleep(4)

    print(f"\nMotor RAG listo con {len(bd_vectorial)} fragmentos indexados.")

    while True:
        user_input = input("\nTu: ")
        if user_input.lower() == "salir":
            break

        print("Seleccion de los documentos mas pertinentes")
        
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

            top_3_documentos = resultados_busqueda[:3]
            
            contexto_recuperado = "DOCUMENTOS RECUPERADOS PARA CONTEXTO:\n"
            print("  -> Archivos seleccionados para esta pregunta:")
            for similitud, doc in top_3_documentos:
                print(f"     * {doc['nombre']} (Relevancia: {similitud:.4f})")
                contexto_recuperado += f"\n--- ARCHIVO: {doc['nombre']} ---\n{doc['texto']}\n"

            prompt_rag_final = f"Peticion del usuario: {user_input}\n\n{contexto_recuperado}"

            print("Generando configuracion...")
            
            response = client.models.generate_content(
                model=model_gen,
                contents=prompt_rag_final,
                config=configuration_rol
            )
            
            print("\nGemini: Exportando configuracion a archivos PDF y YAML.IN")
            
            texto_yaml = response.text.replace("```yaml", "").replace("```", "").strip()
            
            timestamp_actual = int(time.time())
            
            # Generacion de archivo PDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.set_font("Courier", size=9)
            
            for linea in texto_yaml.split('\n'):
                linea_segura = linea.encode('latin-1', 'replace').decode('latin-1')
                pdf.cell(0, 5, txt=linea_segura, ln=True)
            
            nombre_pdf = f"config_open5gs_{timestamp_actual}.pdf"
            pdf.output(nombre_pdf)
            print(f"PDF generado con exito. Guardado como: {nombre_pdf}")
            
            # Generacion de archivo YAML.IN
            nombre_yaml = f"config_open5gs_{timestamp_actual}.yaml.in"
            with open(nombre_yaml, "w", encoding="utf-8") as archivo_yaml:
                archivo_yaml.write(texto_yaml)
            print(f"YAML generado con exito. Guardado como: {nombre_yaml}")
            
        except Exception as e:
            if "429" in str(e):
                print("\nError de API: Cuota excedida. Por favor, espera un minuto y vuelve a escribir tu mensaje.")
            else:
                print(f"\nError de API: {e}")

if __name__ == "__main__":
    chat_terminal()