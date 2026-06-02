# --- CODIGO DE PRUEBA PARA LA ARQUITECTURA HIBRIDA CAG+RAG EN EL CONTEXTO DE CONFIGURACIONES 5G --- 
# Autor: Alejandro R. Sarabia
# Fecha: 28 Mayo 2026

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

# sim_cos: Función encargada de calcular la simulitud entre dos vectores
#          empleada para comparar el prompt introducido con el contenido
#          de los documentos vectorizados en la base de datos.

def sim_cos(vec1, vec2):
    return np.dot(vec1, vec2)/(np.linalg.norm(vec1) * np.linalg.norm(vec2))

def chat_terminal():
    
    print("\n[1/4] Iniciando Arquitectura Hibrida: Construyendo CAG (Memoria Estatica)...")
    
    # Carga de los archivos de configuración base (CAG) que emplearemos como 
    # plantillas para poder generar las configuraciones finales. 

    rutas_cag = [
        "/home/alejandroro/TFG_5G_LLM/CONFIGS/docker-compose.yml",
        "/home/alejandroro/TFG_5G_LLM/CONFIGS/gnb_zmq.yaml",
        "/home/alejandroro/TFG_5G_LLM/CONFIGS/ue_zmq.conf",
    ]

    ruta_ue = "/home/alejandroro/TFG_5G_LLM/srsRAN_4G/build/srsue"
    ruta_gnb = "/home/alejandroro/TFG_5G_LLM/srsRAN_Project/build/apps/gnb"
    ruta_docker = "/home/alejandroro/TFG_5G_LLM/srsRAN_Project/docker"
    ruta_reporte = "/home/alejandroro/TFG_5G_LLM/DESPLIEGUES"

    contexto_cag = ""

    # Lectura de cada plantilla del CAG que se concatenará en un único bloque
    # de texto que se inyectará directamente en el prompt del sistema.

    for ruta in rutas_cag:
        if os.path.exists(ruta):
            with open(ruta, 'r', encoding='utf-8') as f:
                contexto_cag += f"\n--- PLANTILLA: {os.path.basename(ruta)} ---\n{f.read()}\n"
        else:
            print(f"  Advertencia: No se encontro el archivo CAG {os.path.basename(ruta)}")

    # Inyección del contenido del CAG en el prompt del sistema, junto al rol
    # y demás instrucciones para la generación correcta de las configuraciones.

    prompt_v2 = f"""
        # ROL
        Eres un Ingeniero Senior de Telecomunicaciones especializado en 5G O-RAN.
        Despliegas entornos con srsRAN, OAI y Open5GS sobre Docker.

        # CONTEXTO DE PLANTILLAS BASE (CAG)
        Las siguientes plantillas son tu referencia estructural obligatoria.
        Úsalas como esqueleto. NO modifiques los bloques marcados como [INMUTABLE].
        {contexto_cag}

        # CONTEXTO TEÓRICO 3GPP (RAG)
        Usa este contexto ÚNICAMENTE para decidir valores lógicos y de red
        (SST, PLMN, ARFCN, TAC, slicing). NUNCA para modificar hardware SDR.
        {contexto_cag}

        # JERARQUÍA DE REGLAS (en caso de conflicto, la regla de mayor número prevalece)

        ## REGLA 1 — Coherencia PLMN
        MCC y MNC deben ser idénticos en gNB, UE (IMSI) y Core.
        Formato: MCC={{mcc}}, MNC={{mnc}} → PLMN="{mcc}{mnc}"
        IMSI del UE: {mcc}{mnc}XXXXXXXXXX (10 dígitos tras el MNC)

        ## REGLA 2 — Coherencia de frecuencias
        dl_arfcn y band deben corresponder estrictamente según 3GPP TS 38.101:
        - Banda 3:  dl_arfcn ∈ [361000, 376000]
        - Banda 78: dl_arfcn ∈ [620000, 653333]
        - Banda 41: dl_arfcn ∈ [499200, 537999]
        Si detectas inconsistencia entre los valores solicitados, detente y
        responde SOLO con: ERROR: ARFCN <valor> no corresponde a Banda <valor>.

        ## REGLA 3 — Coherencia SCS
        common_scs y ssb_scs DEBEN ser idénticos. No hay excepciones.

        ## REGLA 4 — Puertos ZMQ cruzados
        gNB tx_port ↔ UE rx_port, y gNB rx_port ↔ UE tx_port.
        Ejemplo: gNB(tx=2000, rx=2001) → UE(tx=2001, rx=2000)

        ## REGLA 5 — IPs y bind_addr [PREVALECE SOBRE TODAS]
        - bind_addr en el YAML del gNB standalone: usar la IP del contenedor gNB ()
        - bind_addr en el bloque gnb_compose_config del docker-compose: usar 0.0.0.0
        - Nunca usar 0.0.0.0 como bind_addr en el YAML standalone del gNB
        Justificación: el YAML standalone se ejecuta dentro del contenedor donde
        la IP {gnb_ip} sí existe; el compose override aplica en contexto Docker.

        ## REGLA 6 — Bloque ru_sdr [INMUTABLE]
        Copia el bloque ru_sdr EXACTAMENTE como aparece en el CAG.
        No modifiques srate, device_args ni device_driver bajo ninguna circunstancia.

        # VALIDACIÓN PREVIA (ejecuta mentalmente antes de generar)
        Antes de escribir cualquier archivo, verifica internamente:
        [ ] PLMN es idéntico en los 3 archivos
        [ ] dl_arfcn está dentro del rango de la band configurada  
        [ ] common_scs == ssb_scs
        [ ] Puertos ZMQ están cruzados correctamente
        [ ] bind_addr sigue la REGLA 5 según el contexto (standalone vs compose)
        [ ] ru_sdr no ha sido modificado respecto al CAG
        Si alguna verificación falla, no generes los archivos. Responde con:
        VALIDATION_ERROR: [descripción del problema encontrado]

        # FORMATO DE SALIDA
        Usa ÚNICAMENTE estos delimitadores. Sin markdown, sin explicaciones fuera de ellos.

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
        [Máximo 10 líneas: decisiones técnicas tomadas y por qué, referenciando RAG o CAG]
        ---END_NOTES---
        """
    
    # Generación de la configuración del modelo con el prompt del sistema.

    configuration_rol = types.GenerateContentConfig(
        system_instruction=prompt_v2,
        temperature=0.1
    )

    print("[2/4] Preparando Arquitectura RAG (Memoria Dinamica para PDFs)...")

    # Creación de la base de datos vectorial, pasaremos además de los archivos de configuración
    # que servirán como ejemplo para el modelo, otros manuales que aportarán el contexto necesario.

    rutas_rag = [
        "/home/alejandroro/TFG_5G_LLM/CONFIGS/ts_123501v160600p.pdf",
        "/home/alejandroro/TFG_5G_LLM/CONFIGS/O-RAN.WG1.TR.Use-Cases-Analysis-Report-R005-v19.00-1.pdf",
        "/home/alejandroro/TFG_5G_LLM/CONFIGS/ejemplos_configuraciones2_5g.pdf",
        "/home/alejandroro/TFG_5G_LLM/CONFIGS/ts_123501v150200p.pdf",
        "/home/alejandroro/TFG_5G_LLM/CONFIGS/ejemplos_configuraciones_5g.pdf",
        "/home/alejandroro/TFG_5G_LLM/CONFIGS/2406.01485v1.pdf",
        "/home/alejandroro/TFG_5G_LLM/CONFIGS/1285613.pdf",
        "/home/alejandroro/TFG_5G_LLM/CONFIGS/267704.2677053.pdf",
        "/home/alejandroro/TFG_5G_LLM/CONFIGS/AI-Driven_Zero_Touch_Network_and_Service_Management_in_5G_and_Beyond_Challenges_and_Research_Directions.pdf",
        "/home/alejandroro/TFG_5G_LLM/CONFIGS/Comparative E2E Performance Analysis of O-RAN_0ADesigns in a 5G Standalone Testbed.pdf",
        "/home/alejandroro/TFG_5G_LLM/CONFIGS/Control_Plane_Performance_Benchmarking_and_Feature_Analysis_of_Popular_Open-Source_5G_Core_Networks_OpenAirInterface_Open5GS_and_free5GC.pdf",
        "/home/alejandroro/TFG_5G_LLM/CONFIGS/getPDF.pdf",
        "/home/alejandroro/TFG_5G_LLM/CONFIGS/LLM-enabled_Intent-driven_Service_Configuration_for_Next_Generation_Networks.pdf"
    ]       

    archivo_bd_local = "base_datos_5g_tfg.pkl"
    bd_vectorial = []

    # Función encarga de cargar la base de datos vectorial local si existe.

    if os.path.exists(archivo_bd_local):
        print(f"  -> Cargando base de datos vectorial local desde '{archivo_bd_local}'...")
        with open(archivo_bd_local, 'rb') as f:
            bd_vectorial = pickle.load(f)
        print(f"  -> Carga completada.")
    
    # En caso de que no exista la base de datos, se extrae el contenido de 
    # los archivos que le hemos pasado.

    documentos_extraidos = []
    print("  -> Verificando archivos fuente...")
    for ruta in rutas_rag:
        if not os.path.exists(ruta):
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
                except Exception as e:
                    pass
        else:
                try:
                    with open(ruta, 'r', encoding='utf-8') as f:
                        contenido = f.read()
                        if contenido and contenido.strip():
                            documentos_extraidos.append({
                                "nombre": os.path.basename(ruta),
                                "texto": contenido
                            })
                except Exception as e:
                    pass

    #  Filtrado de documentos ya vectorizados.

    nombres_ya_procesados = {doc["nombre"] for doc in bd_vectorial}
    documentos_a_procesar = [doc for doc in documentos_extraidos if doc["nombre"] not in nombres_ya_procesados]

    total_faltantes = len(documentos_a_procesar)
    
    # Vectorización de los documentos que faltan, además de un guardado progresivo
    # cada diez páginas para que en caso de fallo de la API no perder el contenido.

    if total_faltantes > 0:
        print(f"\n[3/4] Faltan por vectorizar {total_faltantes} documentos. Reanudando proceso...")
        for i, doc in enumerate(documentos_a_procesar):
            exito = False
            intentos = 0
            while not exito and intentos < 5: 
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
                    print(f"  [{i+1}/{total_faltantes}] Vectorizado: {doc['nombre']}")
                    
                    # Bloque de código encargado del guardado progresivo.

                    if (i + 1) % 10 == 0 or (i + 1) == total_faltantes:
                        with open(archivo_bd_local, 'wb') as f:
                            pickle.dump(bd_vectorial, f)
                        print("  [+] Checkpoint guardado. Progreso a salvo.")
                    
#                    time.sleep(1) 
                
                # Excepción encargada de detectar los límites de rendimiento de la API,
                # pausa la vectorización de los archivos de forma exponencial según el
                # número de intentos.

                except Exception as e:
                    if "429" in str(e):
                        intentos += 1
                        espera = 60 * intentos 
                        print(f"   Límite API detectado. Pausando {espera}s (Intento {intentos}/5)...")
                        time.sleep(espera)
                    else:
                        print(f"   Error inesperado: {e}")
                        break
            
            # Bloque de código encargado de hacer un dump de la base de datos vectorial
            # y salir del programa en caso de que se haya agotado el número de intentos.

            if not exito:
                print("\n[!] ERROR CRÍTICO: La API de Google ha bloqueado la cuota de forma estricta.")
                print(f"[!] Todo tu progreso hasta el archivo {doc['nombre']} ESTÁ GUARDADO.")
                print("[!] Vuelve a ejecutar el script en unas horas o mañana para terminar lo que falta.")
                with open(archivo_bd_local, 'wb') as f:
                    pickle.dump(bd_vectorial, f)
                exit(1)
    else:
        print("\n[3/4] Base de datos RAG completamente actualizada. No hay documentos nuevos.")

    print(f"\n[4/4] Motor Híbrido CAG+RAG listo con {len(bd_vectorial)} documentos.")

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
            
            # Extraemos las 5 páginas del PDF que mejor responden a la petición
            top_5_documentos = resultados_busqueda[:5]
            
            contexto_recuperado = "--- TEORIA 3GPP RECUPERADA (RAG) ---\n"
            print("  -> Páginas seleccionadas para justificar esta configuración:")
            for similitud, doc in top_5_documentos:
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

            with open(os.path.join(ruta_gnb, f"gnb_zmq.yaml"), "w", encoding="utf-8") as f:
                f.write(gnb_content)
            
            with open(os.path.join(ruta_ue, f"ue_zmq.conf"), "w", encoding="utf-8") as f:
                f.write(ue_content)
            
            with open(os.path.join(ruta_docker, f"docker-compose.yml"), "w", encoding="utf-8") as f:
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

            pdf.output(os.path.join(ruta_reporte, f"despliegue_e2e_{timestamp}.pdf"))
            print(f" Reporte PDF y archivos generados con éxito.")
            
        except Exception as e:
            print(f"\nError de API: {e}")

if __name__ == "__main__":
    chat_terminal()
