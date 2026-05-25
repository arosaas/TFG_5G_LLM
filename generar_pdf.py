import os
from fpdf import FPDF

# 1. Lista de todos los archivos de código que quieres meter en el cerebro del modelo
rutas_archivos = [
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/5gc-no-scp-sepp-1-999-79.yaml.in",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/5gc-no-scp-sepp2-001-01.yaml.in",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/5gc-no-scp-sepp3-315-010.yaml.in",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/5gc-no-scp-sepp-1-999-79.yaml.in",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/5gc-no-scp-sepp2-001-01.yaml.in",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/5gc-no-scp-sepp3-315-010.yaml.in",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/5gc-sepp-1-999-70.yaml.in",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/5gc-sepp2-001-01.yaml.in",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/5gc-sepp3-315-010.yaml.in",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/5gc-tls-sepp3-315-010.yaml.in",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/amf.yml",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/cell_cfg_max_32_ues.yml",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/cell_cfg_max_64_ues.yml",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/cell_cfg_max_128_ues.yml",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/cell_cfg_max_256_ues.yml",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/cell_cfg_max_512_ues.yml",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/cell_cfg_pucch_narrow_bw.yml",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/cu.yml",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/cu_cp.yml",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/cu_up.yml",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/cu_up_f1u_multiple_sockets.yml",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/du_f1u_multiple_sockets.yml",
    "/home/alejandroro/TFG_5G_LLM/CONFIGS/ue_rf.conf",  
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
nombre_salida = "/home/alejandroro/TFG_5G_LLM/CONFIGS/ejemplos_configuraciones_5g.pdf"
pdf.output(nombre_salida)

print(f"\n[+] Proceso terminado. PDF guardado en: {nombre_salida}")