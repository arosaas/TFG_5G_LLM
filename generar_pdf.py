import os
from fpdf import FPDF

# 1. Lista de todos los archivos de código que quieres meter en el cerebro del modelo
# Extraídos de la carpeta /home/alejandroro/TFG_5G_LLM/CONFIGS/2/ (omitiendo el .pdf)
rutas_archivos = [
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/2/B210_AIR_ue_rf.conf",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/2/B210_AIR_ue_rf_n28.conf",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/2/ue.conf",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/2/ue_887_srate_2304_20Mhz.conf",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/2/ue_935_srate_2304_20Mhz.conf",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/2/ue_1842_5_srate_5,76_5Mhz.conf",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/2/ue_1842_5_srate_1152_10Mhz.conf",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/2/X310_AIR_ue_rf.conf",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/2/X310_AIR_ue_rf_n28.conf"
]

# 2. Configuración inicial del PDF
pdf = FPDF()
pdf.set_auto_page_break(auto=True, margin=15)

print("Generando el PDF de ejemplos de configuración para el RAG...\n")

# 3. Procesamos cada archivo
for ruta in rutas_archivos:
    if os.path.exists(ruta):
        pdf.add_page()
        nombre_archivo = os.path.basename(ruta)
        
        pdf.set_font("Helvetica", style='B', size=12)
        pdf.cell(0, 10, txt=f"Ejemplo de configuración real: {nombre_archivo}", ln=True)
        pdf.ln(5)
        
        # CÓDIGO (Usamos Courier que es tipo consola)
        pdf.set_font("Courier", size=8)
        
        with open(ruta, 'r', encoding='utf-8') as f:
            contenido = f.read()
            for linea in contenido.split('\n'):
                linea_segura = linea.encode('latin-1', 'replace').decode('latin-1')
                pdf.cell(0, 4, txt=linea_segura, ln=True)
                
        print(f"[*] Añadido al PDF: {nombre_archivo}")
    else:
        print(f"[!] ARCHIVO NO ENCONTRADO (Saltando): {ruta}")

# 4. Guardamos el resultado final
nombre_salida = "/home/alejandroro/TFG_5G_LLM/CONFIGS/ejemplos_configuraciones2_5g.pdf"
pdf.output(nombre_salida)

print(f"\n[+] Proceso terminado. PDF guardado en: {nombre_salida}")