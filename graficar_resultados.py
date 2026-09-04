# -- ARQUITECTURA HIBRIDA CAG+RAG PARA CONFIGURACIONES 5G -- #
# Autor: Alejandro R. Sarabia
# Fecha 06/2026

"""
Genera los histogramas y gráficos que pide el tutor a partir del CSV
producido por experimento_sensibilidad.py.

Uso:
    python3 graficar_resultados.py --modo temperatura
    python3 graficar_resultados.py --modo topk

Requiere: pandas, matplotlib
    pip install pandas matplotlib --break-system-packages

NOTA: este script solo puede graficar los datos que realmente existan
en resultados_sensibilidad.csv. No genera ni rellena datos ficticios;
si faltan valores para algún parámetro, esos huecos simplemente no
aparecerán en la gráfica.
"""

import argparse
import pandas as pd
import matplotlib.pyplot as plt

CSV_ENTRADA = "resultados_sensibilidad.csv"

# En cuántos grupos se reparten los valores del parámetro (p. ej. las 7
# temperaturas). Con NGRUPOS = 2 y 7 valores, quedan 3 en el primer grupo
# y 4 en el segundo, tal y como se pidió. Ajusta este número si quieres
# más o menos grupos (y por tanto más o menos filas en la figura).
NGRUPOS = 1


def _dividir_en_grupos(valores, n_grupos):
    """Reparte 'valores' en n_grupos, dejando los grupos más grandes al final."""
    n = len(valores)
    n_grupos = min(n_grupos, n)
    tam_base = n // n_grupos
    resto = n % n_grupos
    grupos, inicio = [], 0
    for i in range(n_grupos):
        tam = tam_base + (1 if i >= n_grupos - resto else 0)
        grupos.append(valores[inicio:inicio + tam])
        inicio += tam
    return grupos


def _figura_combinada(valores, errores_por_valor, tiempos_por_valor,
                       titulo_prefijo, titulo_general, nombre_archivo):
    grupos = _dividir_en_grupos(valores, NGRUPOS)
    ncols = max(len(g) for g in grupos)
    nrows = 2 * len(grupos)  # 2 filas (errores, tiempo) por cada grupo

    fig, axes = plt.subplots(nrows, ncols, figsize=(3.3 * ncols, 3.3 * nrows), squeeze=False)

    for g_idx, grupo in enumerate(grupos):
        fila_errores = 2 * g_idx
        fila_tiempo = 2 * g_idx + 1

        for col_idx in range(ncols):
            if col_idx >= len(grupo):
                axes[fila_errores][col_idx].axis("off")
                axes[fila_tiempo][col_idx].axis("off")
                continue

            valor = grupo[col_idx]

            errores = errores_por_valor[valor]
            pesos_e = [100.0 / len(errores)] * len(errores) if errores else []
            ax_e = axes[fila_errores][col_idx]
            ax_e.hist(errores, bins=[-0.5, 0.5, 1.5, 2.5], rwidth=0.8,
                      weights=pesos_e, color="#ACD7F2", edgecolor="#333")
            ax_e.set_title(f"{titulo_prefijo} {valor}")
            ax_e.set_xlabel("Nº de errores")
            ax_e.set_xticks([0, 1, 2])
            ax_e.set_ylim(0, 100)
            if col_idx == 0:
                ax_e.set_ylabel("% ejecuciones\n(errores)")

            tiempos = tiempos_por_valor[valor]
            pesos_t = [100.0 / len(tiempos)] * len(tiempos) if tiempos else []
            ax_t = axes[fila_tiempo][col_idx]
            ax_t.hist(tiempos, bins=10, weights=pesos_t, color="#bbb651", edgecolor="#333")
            ax_t.set_xlabel("Tiempo de ejecución (s)")
            ax_t.set_ylim(0, 100)
            if col_idx == 0:
                ax_t.set_ylabel("% ejecuciones\n(tiempo)")

    fig.suptitle(titulo_general)
    fig.tight_layout()
    fig.savefig(nombre_archivo, dpi=150)
    print(f"Guardado: {nombre_archivo}")


def graficar_temperatura(df):
    temps = sorted(df["parametro_valor"].unique())
    errores_por_temp, tiempos_por_temp = {}, {}
    for temp in temps:
        subset = df[df["parametro_valor"] == temp]
        errores_por_temp[temp] = subset.apply(
            lambda r: int(r["error_sintactico"]) + int(r["error_coherencia"]), axis=1
        ).tolist()
        tiempos_por_temp[temp] = subset["tiempo_s"].dropna().tolist()

    _figura_combinada(
        temps, errores_por_temp, tiempos_por_temp,
        titulo_prefijo="T =",
        titulo_general="Evolución de errores y tiempo de ejecución según la temperatura del modelo",
        nombre_archivo="histograma_temperatura.png",
    )


def graficar_topk(df):
    ks = sorted(df["parametro_valor"].unique())
    errores_por_k, tiempos_por_k = {}, {}
    for k in ks:
        subset = df[df["parametro_valor"] == k]
        errores_por_k[k] = subset.apply(
            lambda r: int(r["error_sintactico"]) + int(r["error_coherencia"]), axis=1
        ).tolist()
        tiempos_por_k[k] = subset["tiempo_s"].dropna().tolist()

    _figura_combinada(
        ks, errores_por_k, tiempos_por_k,
        titulo_prefijo="top-k =",
        titulo_general="Evolución de errores y tiempo de ejecución según el nº de fragmentos recuperados (top-k)",
        nombre_archivo="histograma_topk.png",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--modo", choices=["temperatura", "topk"], required=True)
    args = parser.parse_args()

    df = pd.read_csv(CSV_ENTRADA)
    df_modo = df[df["modo"] == args.modo]

    if df_modo.empty:
        raise RuntimeError(f"No hay filas con modo='{args.modo}' en {CSV_ENTRADA}")

    if args.modo == "temperatura":
        graficar_temperatura(df_modo)
    else:
        graficar_topk(df_modo)


if __name__ == "__main__":
    main()