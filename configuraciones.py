# -- ARQUITECTURA HIBRIDA CAG+RAG PARA CONFIGURACIONES 5G -- #
# Autor: Alejandro R. Sarabia
# Fecha 06/2026

import os
from dotenv import load_dotenv

load_dotenv()

## -- Configuración API -- ##

API_KEY = os.getenv("API_KEY", "")
MODEL_GEN = "gemini-2.5-flash"
MODEL_EMB = "gemini-embedding-001"

## -- Configuración rutas de entrada -- ## 

RUTAS_CAG = [
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/docker-compose.yml",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/gnb_zmq.yaml",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/ue_zmq.conf",
]
RUTAS_RAG = [
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/ts_123501v160600p.pdf",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/O-RAN.WG1.TR.Use-Cases-Analysis-Report-R005-v19.00-1.pdf",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/ejemplos_configuraciones2_5g.pdf",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/ts_123501v150200p.pdf",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/ejemplos_configuraciones_5g.pdf",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/1285613.pdf",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/getPDF.pdf"
]
RUTAS_SALIDA = {
    "gnb":    "/home/alejandroro/TFG_5G_LLM/srsRAN_Project/build/apps/gnb",
    "ue":     "/home/alejandroro/TFG_5G_LLM/srsRAN_4G/build/srsue",
    "docker": "/home/alejandroro/TFG_5G_LLM/srsRAN_Project/docker",
    "pdf":    "/home/alejandroro/TFG_5G_LLM/DESPLIEGUES",
}
BD_LOCAL = "base_datos_5g_tfg.pkl"
TOP_K    = 5   # chunks RAG recuperados por consulta
CHUNK_SZ = 800 # caracteres por chunk (chunking fino)
