```python
import numpy as np
```

# -- Cálculo similitud coseno -- ##

```python
def sim_cos(v1, v2):
    n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
    return float(np.dot(v1, v2) / (n1 * n2)) if n1 and n2 else 0.0
```

# -- Extracción de bloques de texto -- ##

```python
def extraer_bloque(texto, inicio, fin):
    try:
        return texto.split(inicio)[1].split(fin)[0].strip()
    except IndexError:
        return ""
```

# -- Chunking del texto -- ##

```python
def chunk_texto(texto, nombre, tam=800):
    """Divide un texto largo en chunks solapados para mejor recuperación."""
    chunks = []
    paso = int(tam * 0.8)  # 20 % de solapamiento
    for i, inicio in enumerate(range(0, len(texto), paso)):
        fragmento = texto[inicio:inicio + tam]
        if fragmento.strip():
            chunks.append({"nombre": f"{nombre}__chunk{i}", "texto": fragmento})
    return chunks
```
