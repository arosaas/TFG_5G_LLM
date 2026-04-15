from google import genai
from google.genai import types
import os
import numpy as np
import time
from fpdf import FPDF

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
    entornos core y RAN utilizando tecnologías como srsRAN,
    OpenAirInterface (OAI) y Open5GS.
    
    # OBJETIVO
    Generar archivos de configuración válidos y listos para producción. 
    El usuario te proporcionará su petición, y el sistema adjuntará 
    automáticamente los fragmentos de configuración más relevantes 
    (RAG) para que los uses como contexto.
    
    # REGLAS ESTRICTAS DE GENERACIÓN
    1. EXTRACCIÓN: Analiza el contexto recuperado (Documentos recuperados) 
    para encontrar las variables necesarias (IPs, MCC, MNC, etc.).
    2. SUSTITUCIÓN: Sustituye las etiquetas (< >) de la plantilla base 
    con los valores extraídos.
    3. CERO ALUCINACIONES: Si falta un dato, usa un valor estándar 
    de Open5GS y añade `# REVISAR: Valor asumido por falta de datos`.
    4. FORMATO DE SALIDA: Devuelve ÚNICAMENTE el código YAML.
    
    # PLANTILLA BASE OBLIGATORIA
    (Se asume la estructura Open5GS estándar definida previamente)
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
        #"/home/alejandroro/Escritorio/TFG/CONFIGS/gnb-999-70-ue-315-010.yaml.in",
        #"/home/alejandroro/Escritorio/TFG/CONFIGS/gnb-999-70-ue-999-70.yaml.in",
        #"/home/alejandroro/Escritorio/TFG/CONFIGS/gnb_rf_b210_fdd_srsUE.yml"
    ]

    bd_vectorial = []

    print("\n Leyendo y Vectorizando archivos...")
    for ruta in rutas_archivos:
        if os.path.exists(ruta):
            with open(ruta, 'r', encoding='utf-8') as f:
                contenido_texto = f.read()
            
            # Generación del embedding (Embedding)
            respuesta_emb = client.models.embed_content(
                model=model_emb,
                contents=contenido_texto
            )
            vector = respuesta_emb.embeddings[0].values
            
            # Almacenamiento en BD temporal
            bd_vectorial.append({
                "nombre": os.path.basename(ruta),
                "texto": contenido_texto,
                "vector": vector
            })
            print(f" Vectorizado: {os.path.basename(ruta)}")
            time.sleep(3)
        else:
            print(f" No encontrado: {os.path.basename(ruta)}")

    print(f"\n Motor RAG listo con {len(bd_vectorial)} documentos indexados.")

    while True:
        user_input = input("\nTú: ")
        if user_input.lower() == "salir":
            break

        print("Selección de los documentos más pertinentes")
        
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

            top_2_documentos = resultados_busqueda[:2]
            
            contexto_recuperado = "DOCUMENTOS RECUPERADOS PARA CONTEXTO:\n"
            print("  -> Archivos seleccionados para esta pregunta:")
            for similitud, doc in top_2_documentos:
                print(f"     * {doc['nombre']} (Relevancia: {similitud:.4f})")
                contexto_recuperado += f"\n--- ARCHIVO: {doc['nombre']} ---\n{doc['texto']}\n"

            prompt_rag_final = f"Petición del usuario: {user_input}\n\n{contexto_recuperado}"

            print(" Generando configuración")
            
            response = client.models.generate_content(
                model=model_gen,
                contents=prompt_rag_final,
                config=configuration_rol
            )
            #print(f"\nGemini:\n{response.text}")
            
            # GENERACIÓN ARCHIVO EN PDF
            
            print(f"\nGemini: Exportando configuración a archivo PDF")
            
            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.set_font("Courier", size=9)
            
            texto_yaml = response.text.replace("```yaml", "").replace("```", "").strip()
            
            for linea in texto_yaml.split('\n'):
                linea_segura = linea.encode('latin-1', 'replace').decode('latin-1')
                pdf.cell(0, 5, txt=linea_segura, ln=True)
            
            nombre_pdf = f"config_open5gs_{int(time.time())}.pdf"
            pdf.output(nombre_pdf)
            print(f"PDF generado con exito. Guardado como: {nombre_pdf}")
            
            # GENERACIÓN ARCHIVO YAML.IN
            
            nombre_yaml = f"config_open5gs_{int(time.time())}.yaml.in"
            with open(nombre_yaml, "w", encoding="utf-8") as archivo_yaml:
                archivo_yaml.write(texto_yaml)
            print(f"YAML generado con exito. Guardado como: {nombre_yaml}")
            
        except Exception as e:
            print(f"\nError de API: {e}")

if __name__ == "__main__":
    chat_terminal()
