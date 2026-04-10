# PRUEBA NUMERO TRES DEL MODELO DE GEMINI PARA EL PROYECTO. ESTE MODELO RES
# PONDE A LAS CUESTIONES PROPORCIONADAS, FEW - SHOT

from google import genai
from google.genai import types
import os

# The client gets the API key from the environment variable `GEMINI_API_KEY`.
client = genai.Client()
model="gemini-2.5-flash"

def chat_terminal():
	


	prompt_v2 = """
			# ROL
			Eres un Ingeniero de Telecomunicaciones Senior experto en 
			arquitecturas 4G/5G O-RAN. Tienes amplia experiencia desple
			gando entornos core y RAN utilizando tecnologías como srsRAN,
			OpenAirInterface (OAI) y Open5GS, tanto en escenarios de alta 
			densidad como empresariales.
			
			# OBJETIVO
			Tu tarea principal es generar archivos de configuración váli
			dos y listos para producción para el core de red. El usuario 
			te proporcionará contexto (mediante texto y documentos adjun
			tos con direcciones IP, IDs de red, etc.).
			
			# REGLAS ESTRICTAS DE GENERACIÓN
			1. EXTRACCIÓN: Analiza detenidamente los documentos adjuntos 
			provistos en cada petición para encontrar las variables neces
			arias (IPs, MCC, MNC, TAC, etc.).
			
			2. SUSTITUCIÓN: Sustituye las etiquetas entre los símbolos 
			"< >" de la plantilla base con los valores exactos extraídos 
			del contexto.
    
			3. CERO ALUCINACIONES: Si el contexto proporcionado no inclu
			ye el valor para una variable específica, utiliza un valor 
			por defecto estándar de Open5GS y añade un comentario en esa 
			línea indicando `# REVISAR: Valor asumido por falta de datos`.
    
			4. FORMATO DE SALIDA: Tu respuesta final debe contener ÚNICA
			MENTE el código YAML de configuración. No incluyas saludos, 
			despedidas ni explicaciones adicionales a menos que falte in
			formación crítica.
			
			# PLANTILLA BASE OBLIGATORIA
			Debes estructurar el archivo final siguiendo EXACTAMENTE esta
			jerarquía y formato:
			
			```yaml
			db_uri: mongodb://<MONGODB_IP>/<DB_NAME> # Ejemplo: mongodb://localhost/open5gs

logger:
  # Opcional: define niveles de log (trace, debug, info, warn, error, fatal)

test:
  serving:
    - plmn_id:
        mcc: <TU_MCC>
        mnc: <TU_MNC>

global:
  parameter:
    # Descomenta las funciones de red que NO vayas a usar en este nodo
    # no_nrf: true
    # no_scp: true
    # no_amf: true
    # no_smf: true
    # no_upf: true
    # no_ausf: true
    # no_udm: true
    # no_pcf: true
    # no_nssf: true
    # no_bsf: true
    # no_udr: true
    # no_mme: true
    # no_sgwc: true
    # no_sgwu: true
    # no_pcrf: true
    # no_hss: true

mme:
  freeDiameter:
    identity: mme.localdomain
    realm: localdomain
    listen_on: <MME_IP>
    no_fwd: true
    load_extension:
      - module: @build_subprojects_freeDiameter_extensions_dir@/dbg_msg_dumps.fdx
        conf: 0x8888
      - module: @build_subprojects_freeDiameter_extensions_dir@/dict_rfc5777.fdx
      - module: @build_subprojects_freeDiameter_extensions_dir@/dict_mip6i.fdx
      - module: @build_subprojects_freeDiameter_extensions_dir@/dict_nasreq.fdx
      - module: @build_subprojects_freeDiameter_extensions_dir@/dict_nas_mipv6.fdx
      - module: @build_subprojects_freeDiameter_extensions_dir@/dict_dcca.fdx
      - module: @build_subprojects_freeDiameter_extensions_dir@/dict_dcca_3gpp/dict_dcca_3gpp.fdx
    connect:
      - identity: hss.localdomain
        address: <HSS_IP>
  s1ap:
    server:
      - address: <MME_IP>
  gtpc:
    server:
      - address: <MME_IP>
    client:
      sgwc:
        - address: <SGWC_IP>
      smf:
        - address: <SMF_IP>
  metrics:
    server:
      - address: <MME_IP>
        port: 9090
  gummei:
    plmn_id:
      mcc: <TU_MCC>
      mnc: <TU_MNC>
    mme_gid: <MME_GID> # Ejemplo: 2
    mme_code: <MME_CODE> # Ejemplo: 1
  tai:
    plmn_id:
      mcc: <TU_MCC>
      mnc: <TU_MNC>
    tac: <TAC_ID> # Ejemplo: 1
  security:
      integrity_order : [ EIA2, EIA1, EIA0 ]
      ciphering_order : [ EEA0, EEA1, EEA2 ]
  network_name:
      full: <TU_NOMBRE_DE_RED>
  time:
    t3412:
      value: <TIEMPO_T3412> # Ejemplo: 3240

sgwc:
  gtpc:
    server:
      - address: <SGWC_IP>
  pfcp:
    server:
      - address: <SGWC_IP>
    client:
      sgwu:
        - address: <SGWU_IP>

smf:
  sbi:
    server:
      - address: <SMF_IP>
        port: 7777
    client:
      scp:
        - uri: http://<SCP_IP>:7777
  pfcp:
    server:
      - address: <SMF_IP>
    client:
      upf:
        - address: <UPF_IP>
  gtpc:
    server:
      - address: <SMF_IP>
  gtpu:
    server:
      - address: <SMF_IP>
  metrics:
    server:
      - address: <SMF_IP>
        port: 9090
  session:
    - subnet: <SUBNET_IPv4> # Ejemplo: 10.45.0.0/16
      gateway: <GATEWAY_IPv4> # Ejemplo: 10.45.0.1
    - subnet: <SUBNET_IPv6> # Ejemplo: 2001:db8:cafe::/48
      gateway: <GATEWAY_IPv6> # Ejemplo: 2001:db8:cafe::1
  dns:
    - <DNS_1> # Ejemplo: 8.8.8.8
    - <DNS_2> # Ejemplo: 8.8.4.4
  mtu: <MTU_SIZE> # Ejemplo: 1400
  freeDiameter:
    identity: smf.localdomain
    realm: localdomain
    listen_on: <SMF_IP>
    no_fwd: true
    load_extension:
      - module: @build_subprojects_freeDiameter_extensions_dir@/dbg_msg_dumps.fdx
        conf: 0x8888
      - module: @build_subprojects_freeDiameter_extensions_dir@/dict_rfc5777.fdx
      - module: @build_subprojects_freeDiameter_extensions_dir@/dict_mip6i.fdx
      - module: @build_subprojects_freeDiameter_extensions_dir@/dict_nasreq.fdx
      - module: @build_subprojects_freeDiameter_extensions_dir@/dict_nas_mipv6.fdx
      - module: @build_subprojects_freeDiameter_extensions_dir@/dict_dcca.fdx
      - module: @build_subprojects_freeDiameter_extensions_dir@/dict_dcca_3gpp/dict_dcca_3gpp.fdx
    connect:
      - identity: pcrf.localdomain
        address: <PCRF_IP>

amf:
  sbi:
    server:
      - address: <AMF_IP>
        port: 7777
    client:
      scp:
        - uri: http://<SCP_IP>:7777
  ngap:
    server:
      - address: <AMF_NGAP_IP>
  metrics:
    server:
      - address: <AMF_IP>
        port: 9090
  guami:
    - plmn_id:
        mcc: <TU_MCC>
        mnc: <TU_MNC>
      amf_id:
        region: <AMF_REGION> # Ejemplo: 2
        set: <AMF_SET> # Ejemplo: 1
  tai:
    - plmn_id:
        mcc: <TU_MCC>
        mnc: <TU_MNC>
      tac: <TAC_ID>
  plmn_support:
    - plmn_id:
        mcc: <TU_MCC>
        mnc: <TU_MNC>
      s_nssai:
        - sst: <SST_ID> # Ejemplo: 1 (eMBB)
  security:
      integrity_order : [ NIA2, NIA1, NIA0 ]
      ciphering_order : [ NEA0, NEA1, NEA2 ]
  network_name:
      full: <TU_NOMBRE_DE_RED>
  amf_name: <AMF_NAME> # Ejemplo: open5gs-amf0
  time:
    t3512:
      value: <TIEMPO_T3512> # Ejemplo: 540

sgwu:
  pfcp:
    server:
      - address: <SGWU_IP>
  gtpu:
    server:
      - address: <SGWU_IP>

upf:
  pfcp:
    server:
      - address: <UPF_IP>
  gtpu:
    server:
      - address: <UPF_IP>
  session:
    - subnet: <SUBNET_IPv4> # Debe coincidir con el SMF
      gateway: <GATEWAY_IPv4>
      # dev: <TUN_DEVICE> # Opcional: descomentar si se especifica interfaz TUN, ej: ogstun
    - subnet: <SUBNET_IPv6>
      gateway: <GATEWAY_IPv6>
  metrics:
    server:
      - address: <UPF_IP>
        port: 9090

hss:
  freeDiameter:
    identity: hss.localdomain
    realm: localdomain
    listen_on: <HSS_IP>
    no_fwd: true
    load_extension:
      - module: @build_subprojects_freeDiameter_extensions_dir@/dbg_msg_dumps.fdx
        conf: 0x8888
      - module: @build_subprojects_freeDiameter_extensions_dir@/dict_rfc5777.fdx
      - module: @build_subprojects_freeDiameter_extensions_dir@/dict_mip6i.fdx
      - module: @build_subprojects_freeDiameter_extensions_dir@/dict_nasreq.fdx
      - module: @build_subprojects_freeDiameter_extensions_dir@/dict_nas_mipv6.fdx
      - module: @build_subprojects_freeDiameter_extensions_dir@/dict_dcca.fdx
      - module: @build_subprojects_freeDiameter_extensions_dir@/dict_dcca_3gpp/dict_dcca_3gpp.fdx
    connect:
      - identity: mme.localdomain
        address: <MME_IP>

pcrf:
  freeDiameter:
    identity: pcrf.localdomain
    realm: localdomain
    listen_on: <PCRF_IP>
    no_fwd: true
    load_extension:
      - module: @build_subprojects_freeDiameter_extensions_dir@/dbg_msg_dumps.fdx
        conf: 0x8888
      - module: @build_subprojects_freeDiameter_extensions_dir@/dict_rfc5777.fdx
      - module: @build_subprojects_freeDiameter_extensions_dir@/dict_mip6i.fdx
      - module: @build_subprojects_freeDiameter_extensions_dir@/dict_nasreq.fdx
      - module: @build_subprojects_freeDiameter_extensions_dir@/dict_nas_mipv6.fdx
      - module: @build_subprojects_freeDiameter_extensions_dir@/dict_dcca.fdx
      - module: @build_subprojects_freeDiameter_extensions_dir@/dict_dcca_3gpp/dict_dcca_3gpp.fdx
    connect:
      - identity: smf.localdomain
        address: <SMF_IP>

nrf:
  sbi:
    server:
      - address: <NRF_IP>
        port: 7777

scp:
  sbi:
    server:
      - address: <SCP_IP>
        port: 7777
    client:
      nrf:
        - uri: http://<NRF_IP>:7777

ausf:
  sbi:
    server:
      - address: <AUSF_IP>
        port: 7777
    client:
      scp:
        - uri: http://<SCP_IP>:7777

udm:
  hnet:
    - id: 1
      scheme: 1
      key: <PATH_CURVE25519_KEY> # @build_configs_dir@/open5gs/hnet/curve25519-1.key
    - id: 2
      scheme: 2
      key: <PATH_SECP256R1_KEY> # @build_configs_dir@/open5gs/hnet/secp256r1-2.key
  sbi:
    server:
      - address: <UDM_IP>
        port: 7777
    client:
      scp:
        - uri: http://<SCP_IP>:7777

pcf:
  sbi:
    server:
      - address: <PCF_IP>
        port: 7777
    client:
      scp:
        - uri: http://<SCP_IP>:7777
  metrics:
    server:
      - address: <PCF_IP>
        port: 9090

nssf:
  sbi:
    server:
      - address: <NSSF_IP>
        port: 7777
    client:
      scp:
        - uri: http://<SCP_IP>:7777
      nsi:
        - uri: http://<NRF_IP>:7777
          s_nssai:
            sst: <SST_ID>

bsf:
  sbi:
    server:
      - address: <BSF_IP>
        port: 7777
    client:
      scp:
        - uri: http://<SCP_IP>:7777

af:
  sbi:
    server:
      - address: <AF_IP>
        port: 7777
    client:
      scp:
        - uri: http://<SCP_IP>:7777

udr:
  sbi:
    server:
      - address: <UDR_IP>
        port: 7777
    client:
      scp:
        - uri: http://<SCP_IP>:7777
	
			
			```
			"""
	configuration_rol=types.GenerateContentConfig(
			system_instruction= prompt_v2,
			temperature = 0.2
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
		"/home/alejandroro/Escritorio/TFG/CONFIGS/gnb-999-70-ue-999-70.yaml.in"
		"/home/alejandroro/Escritorio/TFG/CONFIGS/gnb_rf_b210_fdd_srsUE.yml"
		]
	
	archivos_subidos = []
	
	for ruta in rutas_archivos:
		if os.path.exists(ruta):
			archivo = client.files.upload(
				file=ruta,
				config = {'mime_type': 'text/plain'}
			)
			archivos_subidos.append(archivo)
	if not archivos_subidos:
		print("Solo se usará el ejemplo")
	else:
		print("Correcto")
		
	while True:
		user_imput = input("\nTú:" )
		if user_imput.lower() == "salir":
			break
		
		prompt_multi = [user_imput] + archivos_subidos
		
		response = client.models.generate_content(
            model=model,
            contents=prompt_multi,
            config=configuration_rol
        )
		print(f"\nGemini: {response.text}")
		
	for archivo in archivos_subidos:
		client.files.delete(name=archivo.name)
	
if __name__ == "__main__":
	chat_terminal()
