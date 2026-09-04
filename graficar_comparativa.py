# -- ARQUITECTURA HIBRIDA CAG+RAG PARA CONFIGURACIONES 5G -- #
# Autor: Alejandro R. Sarabia
# Fecha 06/2026

"""
Genera el histograma comparativo entre "LLM sin RAG/CAG" y "Sistema
propuesto (RAG/CAG)" a partir de resultados_comparativa.csv, usando el
mismo prompt exacto repetido N veces en cada método.

Uso:
    python3 graficar_comparativa.py

Requiere: pandas, matplotlib
"""

import pandas as pd
import matplotlib.pyplot as plt

CSV_ENTRADA = "resultados_comparativa.csv"

ETIQUETAS = {
    "sin_rag_cag": "LLM sin RAG/CAG",
    "sistema_propuesto": "Sistema propuesto (RAG/CAG)",
}


def graficar():
    df = pd.read_csv(CSV_ENTRADA)
    metodos = [m for m in ["sin_rag_cag", "sistema_propuesto"] if m in df["metodo"].unique()]
    ncols = len(metodos)

    fig, axes = plt.subplots(2, ncols, figsize=(4.5 * ncols, 7), squeeze=False)

    for col, metodo in enumerate(metodos):
        subset = df[df["metodo"] == metodo]
        n = len(subset)

        # Fila 1: tasa de éxito / fallo (en %)
        exitos = subset["exito"].sum()
        fallos = n - exitos
        ax_e = axes[0][col]
        ax_e.bar(
            ["Éxito", "Fallo"],
            [100 * exitos / n if n else 0, 100 * fallos / n if n else 0],
            color=["#82b366", "#fccccc"], edgecolor="#333",
        )
        ax_e.set_title(ETIQUETAS.get(metodo, metodo))
        ax_e.set_ylabel("% de ejecuciones")
        ax_e.set_ylim(0, 100)
        for i, valor in enumerate([100 * exitos / n if n else 0, 100 * fallos / n if n else 0]):
            ax_e.text(i, valor + 2, f"{valor:.0f}%", ha="center")

        # Fila 2: distribución del tiempo de ejecución
        ax_t = axes[1][col]
        tiempos = subset["tiempo_s"].dropna()
        pesos = [100.0 / len(tiempos)] * len(tiempos) if len(tiempos) else []
        ax_t.hist(tiempos, bins=10, weights=pesos, color="#bbb651", edgecolor="#333")
        ax_t.set_xlabel("Tiempo de ejecución (s)")
        ax_t.set_ylabel("% de ejecuciones")
        ax_t.set_ylim(0, 100)

    fig.suptitle(
        f"Comparativa LLM sin RAG/CAG vs Sistema propuesto\n"
        f"(mismo prompt, {df.groupby('metodo').size().max()} repeticiones por método)"
    )
    fig.tight_layout()
    fig.savefig("histograma_comparativa.png", dpi=150)
    print("Guardado: histograma_comparativa.png")


if __name__ == "__main__":
    graficar()