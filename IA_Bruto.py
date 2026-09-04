from google import genai
from dotenv import load_dotenv
import os
import datetime

load_dotenv()
API_KEY = os.getenv("API_KEY", "")
# The client gets the API key from the environment variable `GEMINI_API_KEY`.
client = genai.Client(api_key=API_KEY)

start = datetime.datetime.now()
response = client.models.generate_content(
    model="gemini-2.5-flash", contents="    Configura un entorno O-RAN E2E completo para un caso de comunicaciones vehiculares V2X en una autopista inteligente. Busca en la base de datos RAG el valor SST estandarizado correspondiente a eMBB, requerido para aplicaciones de seguridad vial con latencias sub-10ms y aplicalo al bloque tai_slice_support_list del gNB anadiendo un comentario YAML que indique la seccion o tabla del estandar de la que has extraido el valor. Configura la red PLM con MCC 214, MNC 01 y TAC 7. Usa la Banda 41 con dl_arfcn 500000, ancho de banda de 10 MHz y SCS de 15 kHZ. Estos parametros son obligatorios porque deben ser compatibles con la tasa de muestreo de 11.52 Mbps impuesta por el entorno ZMQ. La duracion de la sesion debe configurarse a 45 minutos. Para el enlace de radio virtual ZMQ, cruza los puertos 2000 y 2001 entre el gNB y el UE. La IP del contenedor gNB sera 10.20.2.1 y la del core de Open5GS sera 10.20.2.2, que coincidira con la direccion AMF. El UE debe utilizar el algoritmo Milenage con los siguientes parametros de autenticacion: IMSI: 214010000000001, K: 00aabbccddeeff112233445566778899, OPC:112233445566778899aabbccddeeff00. Activa las metricas de RLC y del scheduler DU con un periodo de reporte de 600 ms para monitorizar la latencia del plano de usuario en tiempo real. Habilita tambien las capturas PCAP de NGAP. Debes crear tres archivos, uno para el nodo gNB, otro para el UE y otro para el 5gc, que opera con un docker"
)
print(response.text)
end = datetime.datetime.now()
total_time = (end - start).total_seconds()
print(f"\nTiempo total: {total_time:.2f} segundos")