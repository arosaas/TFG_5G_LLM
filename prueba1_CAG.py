from google import genai
from google.genai import types
import os
import time
from fpdf import FPDF
import PyPDF2

client = genai.Client()

model_gen = "gemini-2.5-flash"

def chat_terminal():
    
    prompt_v2 = """
    # ROL
    Eres un Ingeniero de Telecomunicaciones Senior experto en 
    arquitecturas 4G/5G O-RAN. Tienes amplia experiencia desplegando 
    entornos core y RAN utilizando tecnologias como srsRAN,
    OpenAirInterface (OAI) y Open5GS.
    
    # OBJETIVO
    Generar archivos de configuracion validos y listos para produccion. 
    El usuario te proporcionara su peticion, y tú debes utilizar el 
    CONOCIMIENTO BASE GLOBAL proporcionado en tus instrucciones del sistema 
    para extraer las configuraciones necesarias.
    
    # REGLAS ESTRICTAS DE GENERACION
    1. EXTRACCION: Analiza el contexto técnico cargado en tu memoria para 
    encontrar las variables necesarias (IPs, MCC, MNC, etc.) o instrucciones tecnicas.
    2. SUSTITUCION: Sustituye las etiquetas (< >) de las plantillas base 
    con los valores extraidos.
    3. CERO ALUCINACIONES: Si falta un dato, usa un valor estandar 
    de Open5GS y añade `# REVISAR: Valor asumido por falta de datos`.
    4. FORMATO DE SALIDA: Devuelve UNICAMENTE el codigo YAML. No añadas texto introductorio.
    """

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
        "/home/alejandroro/Escritorio/TFG/CONFIGS/gnb_rf_b210_fdd_srsUE.yml",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/Comparative E2E Performance Analysis of O-RAN_0ADesigns in a 5G Standalone Testbed.pdf",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/AI-Driven_Zero_Touch_Network_and_Service_Management_in_5G_and_Beyond_Challenges_and_Research_Directions.pdf",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/Control_Plane_Performance_Benchmarking_and_Feature_Analysis_of_Popular_Open-Source_5G_Core_Networks_OpenAirInterface_Open5GS_and_free5GC.pdf",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/5gc-no-scp-sepp1-999-70.yaml.in",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/5gc-no-scp-sepp2-001-01.yaml.in",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/5gc-no-scp-sepp3-315-010.yaml.in",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/5gc-sepp1-999-70.yaml.in",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/5gc-sepp2-001-01.yaml.in",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/5gc-sepp3-315-010.yaml.in",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/amf.yml",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/cell_cfg_max_32_ues.yml",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/cell_cfg_max_64_ues.yml",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/cell_cfg_max_128_ues.yml",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/cell_cfg_max_256_ues.yml",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/cell_cfg_max_512_ues.yml",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/cell_cfg_pucch_narrow_bw.yml",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/cu_cp.yml",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/cu_up_f1u_multiple_sockets.yml",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/cu_up.yml",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/cu.yml",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/debug.yml",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/du_f1u_multiple_sockets.yml",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/du_rf_b200_tdd_n78_20mhz.yml",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/geo_ntn.yml",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/gnb_custom_cell_properties.yml",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/gnb_rf_b200_tdd_n78_20mhz.yml",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/gnb_rf_n310_fdd_n3_20mhz.yml",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/gnb_ru_picocom_scb_tdd_n78_20mhz.yml",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/gnb_ru_ran550_tdd_n78_100mhz_4x2.yml",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/gnb_ru_rpqn4800e_tdd_n78_20mhz_2x2.yml",
        "/home/alejandroro/Escritorio/TFG/CONFIGS/gnb_zmq.yaml"
    ]

    print("\nFase 1: Extrayendo texto y consolidando el Contexto Global (CAG)...")
    contexto_global = "=== CONOCIMIENTO BASE GLOBAL (ARCHIVOS Y MANUALES) ===\n\n"
    documentos_procesados = 0

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
                            nombre_doc = f"{os.path.basename(ruta)} - Pag {num_pagina + 1}"
                            contexto_global += f"--- {nombre_doc} ---\n{texto_pagina}\n\n"
                documentos_procesados += 1
                print(f"  Extraido PDF al contexto: {os.path.basename(ruta)}")
            except Exception as e:
                print(f"Error al leer el PDF {os.path.basename(ruta)}: {e}")
        else:
            with open(ruta, 'r', encoding='utf-8') as f:
                contenido_texto = f.read()
            contexto_global += f"--- ARCHIVO DE CONFIGURACION: {os.path.basename(ruta)} ---\n{contenido_texto}\n\n"
            documentos_procesados += 1

    print("\nFase 2: Configurando el modelo Gemini con la memoria inyectada...")
    
    instruccion_sistema_completa = f"{prompt_v2}\n\n{contexto_global}"

    configuration_rol = types.GenerateContentConfig(
        system_instruction=instruccion_sistema_completa,
        temperature=0.2
    )

    print(f"\nMotor CAG listo. {documentos_procesados} documentos cargados directamente en la memoria del modelo.")

    while True:
        user_input = input("\nTu: ")
        if user_input.lower() == "salir":
            break

        print("Analizando peticion y generando configuracion...")
        
        try:
            response = client.models.generate_content(
                model=model_gen,
                contents=user_input,
                config=configuration_rol
            )
            
            print("Gemini: Exportando configuracion a archivos PDF y YAML.IN")
            
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
                print("\nError de API: Cuota excedida. Por favor, espera un minuto.")
            else:
                print(f"\nError de API: {e}")

if __name__ == "__main__":
    chat_terminal()