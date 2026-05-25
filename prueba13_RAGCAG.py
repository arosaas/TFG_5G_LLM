# --- CODIGO DE PRUEBA PARA LA ARQUITECTURA HIBRIDA CAG+RAG EN EL CONTEXTO DE CONFIGURACIONES 5G --- 
# Autor: Alejandro R. Sarabia
# Fecha: Mayo 2026

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
        Eres un Ingeniero de Telecomunicaciones Senior experto en arquitecturas 4G/5G O-RAN. 
        Tienes amplia experiencia desplegando entornos core y RAN utilizando tecnologías como srsRAN,
        OpenAirInterface (OAI) y Open5GS sobre entornos contenedorizados con Docker.
        
        # OBJETIVO
        Generar simultáneamente tres archivos de configuración válidos (gNB, UE, Docker).

        # CONOCIMIENTO BASE GLOBAL (CAG)
        Utiliza estrictamente la estructura de estas plantillas YAML, YML y CONF que tienes en tu memoria base:
        {contexto_cag}

        # INSTRUCCIONES DE GENERACIÓN
        Además del conocimiento base global (CAG), debes cruzar esta información con la teoría recuperada de los documentos 3GPP (RAG) para generar configuraciones coherentes y justificadas.
        - El gNB debe configurarse con parámetros técnicos realistas y coherentes con el estándar 3GPP, utilizando la información recuperada del RAG para fundamentar cada valor.
        - El UE debe tener una configuración que refleje un dispositivo móvil típico, con parámetros que se correspondan con los del gNB y que estén justificados por la teoría del RAG.   
        - El docker-compose.yml debe contener los servicios necesarios para desplegar el gNB y el UE, con puertos y redes que permitan la comunicación entre ambos, y que estén alineados con las configuraciones de red definidas en el gNB y el UE.
        Deberás mostrar además por pantalla un tutorial siguiendo la información que aparece en https://docs.srsran.com/projects/project/en/latest/tutorials/source/srsUE/source/index.html
        en el apartado ZeroMQ-based Setup para explicar cómo se realizan las pruebas de conectividad.
        
        # REGLAS ESTRICTAS DE COHERENCIA E2E
        - El MCC y MNC deben ser idénticos en el gNB, en el UE (IMSI) y en el Core.
        - Las direcciones IP deben mapearse correctamente entre los tres ficheros según las redes definidas.
        - Los puertos TCP de ZMQ del gNB deben cruzarse de forma inversa con los del UE.
        - Utiliza la teoría recuperada del estándar 3GPP (que el usuario te pasará como contexto) para fundamentar los valores técnicos de Slicing, QCI, etc.
        - OBLIGATORIO: Asegúrate de que el canal de frecuencia (dl_arfcn) corresponda exactamente con la banda (band) elegida. Nunca mezcles bandas. Por ejemplo, si usas la Banda 3, el dl_arfcn debe estar estrictamente entre 361000 y 376000. Si decides usar el dl_arfcn 620000, asegúrate de configurar la banda 78.
        - OBLIGATORIO: En el archivo docker-compose.yml, debes asignar estáticamente las direcciones IP (usando 'ipv4_address') a cada contenedor para que coincidan con las configuradas en los archivos del gNB y el UE.
        - OBLIGATORIO: El valor de "common_scs" y el de "ssb_scs" (o cualquier referencia al Sub-Carrier Spacing del SSB) DEBEN SER EXACTAMENTE IGUALES en el archivo del gNB. srsRAN no soporta que sean diferentes.
        - MUY IMPORTANTE (ERROR DE BIND UDP): En TODOS los archivos generados (tanto en el YAML del gNB principal como en el docker-compose.yml), CUALQUIER parámetro 'bind_addr' DEBE tener el valor exacto '0.0.0.0'. Bajo ningún concepto uses la IP 10.53.1.3 para los binds.
- OBLIGATORIO: No alteres ni inventes parámetros de hardware de radio o tasas de muestreo. Debes copiar el bloque 'ru_sdr' (incluyendo los valores de 'srate' y 'device_args') EXACTAMENTE igual que como aparece en las plantillas base (CAG). Utiliza la teoría del RAG únicamente para la configuración lógica y de red (SST, PLMN, ARFCN), no para modificar la configuración física del SDR.

        # FORMATO OBLIGATORIO DE SALIDA
        Estructura tu respuesta única y exclusivamente usando los siguientes bloques delimitadores. 
        NO uses bloques de código markdown (```yaml) dentro de los delimitadores. Devuelve solo texto plano.

        ---START_GNB---
        [Código YAML del gNB]
        ---END_GNB---

        ---START_UE---
        [Código del .conf del UE]
        ---END_UE---

        ---START_DOCKER---
        [Código del docker-compose.yml]
        ---END_DOCKER---
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
        "/home/alejandroro/TFG_5G_LLM/CONFIGS/ejemplos_configuraciones_5g.pdf"
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
                    
                    time.sleep(4) 
                
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