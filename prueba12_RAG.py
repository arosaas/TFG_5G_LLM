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
    
    prompt_v2 = """
    # ROL
    Eres un Ingeniero de Telecomunicaciones Senior experto en arquitecturas 4G/5G O-RAN. 
    Tienes amplia experiencia desplegando entornos core y RAN utilizando tecnologías como srsRAN,
    OpenAirInterface (OAI) y Open5GS sobre entornos contenedorizados con Docker.
    
    # OBJETIVO
    Generar simultáneamente tres archivos de configuración válidos, coherentes entre sí y listos para producción:
    1. gNB Config (Formato YAML para srsRAN Project gNB)
    2. UE Config (Formato de texto plano .conf para srsUE ZMQ)
    3. Docker Compose (Formato YAML para docker-compose.yml)

    # REGLAS ESTRICTAS DE COHERENCIA E2E
    - El MCC y MNC deben ser idénticos en el gNB, en el UE (IMSI) y en el Core del Docker Compose.
    - Las direcciones IP de control plane (AMF) e interfaces de radio virtuales (ZMQ) deben mapearse correctamente entre los tres ficheros según las redes definidas.
    - Los puertos TCP de ZMQ del gNB deben cruzarse de forma inversa con los del UE (ej. tx_port gNB -> rx_port UE).
    - Utiliza la teoría técnica recuperada del estándar 3GPP (Contexto RAG) para fundamentar los valores técnicos si se te solicitan en el prompt.

    # FORMATO OBLIGATORIO DE SALIDA
    Debes estructurar tu respuesta única y exclusivamente usando los siguientes bloques delimitadores. 
    No agregues introducciones, saludos ni conclusiones. Respeta escrupulosamente las identaciones de los ejemplos.

    ---START_GNB---
    cu_cp:
      amf:
        addr: 10.53.1.2
        port: 38412
        bind_addr: 10.53.1.1
        supported_tracking_areas:
          - tac: 7
            plmn_list:
              - plmn: "00101"
                tai_slice_support_list:
                  - sst: 1
      inactivity_timer: 7200

    ru_sdr:
      device_driver: zmq
      device_args: tx_port=tcp://127.0.0.1:2000,rx_port=tcp://127.0.0.1:2001,base_srate=11.52e6
      srate: 11.52
      tx_gain: 75
      rx_gain: 75

    cell_cfg:
      dl_arfcn: 368500
      band: 3
      channel_bandwidth_MHz: 10
      common_scs: 15
      plmn: "00101"
      tac: 7
      pdcch:
        common:
          ss0_index: 0
          coreset0_index: 6
        dedicated:
          ss2_type: common
          dci_format_0_1_and_1_1: false
      prach:
        prach_config_index: 1
      pdsch:
        mcs_table: qam64
      pusch:
        mcs_table: qam64

    log:
      filename: /tmp/gnb.log
      all_level: info
      hex_max_size: 0

    pcap:
      mac_enable: false
      mac_filename: /tmp/gnb_mac.pcap
      ngap_enable: false
      ngap_filename: /tmp/gnb_ngap.pcap
      e2ap_enable: true
      e2ap_du_filename: /tmp/gnb_du_e2ap.pcap
      e2ap_cu_cp_filename: /tmp/gnb_cu_cp_e2ap.pcap
      e2ap_cu_up_filename: /tmp/gnb_cu_up_e2ap.pcap

    metrics:
      layers:
        enable_rlc: true
        enable_sched: true
      periodicity:
        du_report_period: 1000
    ---END_GNB---

    ---START_UE---
    [rf]
    freq_offset = 0
    tx_gain = 50
    rx_gain = 40
    srate = 11.52e6
    nof_antennas = 1
    device_name = zmq
    device_args = tx_port=tcp://127.0.0.1:2001,rx_port=tcp://127.0.0.1:2000,base_srate=11.52e6

    [rat.eutra]
    dl_earfcn = 2850
    nof_carriers = 0

    [rat.nr]
    bands = 3
    nof_carriers = 1

    [pcap]
    enable = none
    mac_filename = /tmp/ue_mac.pcap
    mac_nr_filename = /tmp/ue_mac_nr.pcap
    nas_filename = /tmp/ue_nas.pcap

    [log]
    all_level = warning
    phy_lib_level = none
    all_hex_limit = 32
    filename = stdout
    file_max_size = -1

    [usim]
    mode = soft
    algo = milenage
    opc  = 63BFA50EE6523365FF14C1F45F88737D
    k    = 00112233445566778899aabbccddeeff
    imsi = 001010123456780
    imei = 353490069873319

    [rrc]
    release = 15
    ue_category = 4

    [nas]
    apn = srsapn
    apn_protocol = ipv4

    [gw]
    netns = ue1
    ip_devname = tun_srsue
    ip_netmask = 255.255.255.0

    [gui]
    enable = false
    ---END_UE---

    ---START_DOCKER---
    services:
      5gc:
        container_name: open5gs_5gc
        build:
          context: open5gs
          target: open5gs
          args:
            OS_VERSION: "22.04"
            OPEN5GS_VERSION: "v2.7.0"
        env_file:
          - ${OPEN_5GS_ENV_FILE:-open5gs/open5gs.env}
        privileged: true
        ports:
          - "9898:9999/tcp"
        command: 5gc -c open5gs-5gc.yml
        healthcheck:
          test: [ "CMD-SHELL", "nc -z 127.0.0.20 7777" ]
          interval: 3s
          timeout: 1s
          retries: 60
        networks:
          ran:
            ipv4_address: ${OPEN5GS_IP:-10.53.1.2}

      gnb:
        container_name: srsran_gnb
        image: srsran/gnb
        build:
          context: ..
          dockerfile: docker/Dockerfile
          args:
            OS_VERSION: "24.04"
        privileged: true
        cap_add:
          - SYS_NICE
          - CAP_SYS_PTRACE
        volumes:
          - /dev/bus/usb/:/dev/bus/usb/
          - /usr/share/uhd/images:/usr/share/uhd/images
          - gnb-storage:/tmp
        configs:
          - gnb_config.yml
          - gnb_compose_config.yml
        networks:
          ran:
            ipv4_address: ${GNB_IP:-10.53.1.3}
          metrics:
            ipv4_address: 172.19.1.3
        depends_on:
          5gc:
            condition: service_healthy
        command: gnb -c /gnb_config.yml -c /gnb_compose_config.yml

    configs:
      gnb_config.yml:
        file: ${GNB_CONFIG_PATH:-../configs/gnb_rf_b200_tdd_n78_20mhz.yml}
      gnb_compose_config.yml:
        content: |
          cu_cp:
            amf:
              addr: ${OPEN5GS_IP:-10.53.1.2}
              bind_addr: ${GNB_IP:-10.53.1.3}
          metrics:
            autostart_stdout_metrics: true
            enable_json: true
          remote_control:
            bind_addr: 0.0.0.0
            enabled: true

    volumes:
      gnb-storage:

    networks:
      ran:
        ipam:
          driver: default
          config:
            - subnet: 10.53.1.0/24
      metrics:
        ipam:
          driver: default
          config:
            - subnet: 172.19.1.0/24
    ---END_DOCKER---
    """

    configuration_rol = types.GenerateContentConfig(
        system_instruction=prompt_v2,
        temperature=0.1
    )

    rutas_archivos = [
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
        # Aquí se incluye el PDF subido (Asegúrate de que la ruta sea correcta)
        "/home/alejandroro/TFG_5G_LLM/CONFIGS/ts_123501v160600p.pdf"
    ]

    archivo_bd_local = "base_datos_5g.pkl"
    bd_vectorial = []

    # COMPROBACIÓN DE CACHÉ LOCAL
    if os.path.exists(archivo_bd_local):
        print(f"\n Cargando base de datos vectorial local desde '{archivo_bd_local}'...")
        with open(archivo_bd_local, 'rb') as f:
            bd_vectorial = pickle.load(f)
        print(f" Carga completada en 0 segundos. {len(bd_vectorial)} fragmentos y páginas listos.")
        
    else:
        documentos_extraidos = []
        print("\n Leyendo archivos y extrayendo PDFs (Esto puede tardar)...")
        for ruta in rutas_archivos:
            if not os.path.exists(ruta):
                print(f" No encontrado: {os.path.basename(ruta)}")
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
                    print(f" Error al leer el PDF {os.path.basename(ruta)}: {e}")
            else:
                with open(ruta, 'r', encoding='utf-8') as f:
                    documentos_extraidos.append({
                        "nombre": os.path.basename(ruta),
                        "texto": f.read()
                    })

        total_docs = len(documentos_extraidos)
        print(f"\n Vectorizando {total_docs} fragmentos. Pausa de 5s activa para evitar baneos de Google...")
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
                    print(f" [{i+1}/{total_docs}] Vectorizado: {doc['nombre']}")
                    time.sleep(5) 
                except Exception as e:
                    if "429" in str(e):
                        intentos += 1
                        print(f"  Límite superado. Pausando 60s (Intento {intentos}/3)...")
                        time.sleep(60)
                    else:
                        print(f"  Error inesperado: {e}")
                        break
        
        # GUARDAR EN DISCO AL TERMINAR
        with open(archivo_bd_local, 'wb') as f:
            pickle.dump(bd_vectorial, f)
        print(f"\n Base de datos '{archivo_bd_local}' creada con éxito.")

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
            # Extraemos los 3 documentos más afines (para pillar bien las páginas del PDF)
            top_3_documentos = resultados_busqueda[:3]
            
            contexto_recuperado = "DOCUMENTOS RECUPERADOS PARA CONTEXTO (USA ESTA INFO TÉCNICA):\n"
            print("  -> Archivos/Páginas seleccionadas para esta pregunta:")
            for similitud, doc in top_3_documentos:
                print(f"     * {doc['nombre']} (Relevancia: {similitud:.4f})")
                contexto_recuperado += f"\n--- ORIGEN: {doc['nombre']} ---\n{doc['texto']}\n"

            prompt_rag_final = f"Petición del usuario: {user_input}\n\n{contexto_recuperado}"

            print(" Generando configuraciones E2E...")
            
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

            print(f"\n Exportando configuraciones generadas con ID: {timestamp}")

            with open(f"gnb_zmq_{timestamp}.yaml", "w", encoding="utf-8") as f:
                f.write(gnb_content)
            print(f" Archivo generado: gnb_zmq_{timestamp}.yaml")

            with open(f"ue_zmq_{timestamp}.conf", "w", encoding="utf-8") as f:
                f.write(ue_content)
            print(f" Archivo generado: ue_zmq_{timestamp}.conf")

            with open(f"docker-compose_{timestamp}.yml", "w", encoding="utf-8") as f:
                f.write(docker_content)
            print(f" Archivo generado: docker-compose_{timestamp}.yml")

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
            print(f" Reporte PDF generado con éxito: despliegue_e2e_{timestamp}.pdf")
            
        except Exception as e:
            print(f"\nError de API: {e}")

if __name__ == "__main__":
    chat_terminal()