import os
import time
import pickle
import PyPDF2
import math
import re
import logging
from collections import Counter, defaultdict
from google.genai import types
from utilidades import sim_cos, extraer_bloque, chunk_texto
import configuraciones
from generar_prompt import SYSTEM_PROMPT_TEMPLATE

# Try to import pdfplumber for advanced table extraction
try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False
    logging.getLogger(__name__).warning("pdfplumber not installed. Table extraction from PDFs will be limited.")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("/tmp/5g_config_generator.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

## -- Funciones para TF-IDF (parte de búsqueda híbrida) -- ##

def tokenize_text(text):
    """Simple tokenization: lowercase and split by non-alphanumeric characters."""
    tokens = re.findall(r'\b\w+\b', text.lower())
    return tokens

def compute_tf_idf(documents):
    """
    Compute TF-IDF vectors for a list of documents.
    Returns a tuple of (vocabulary, idf_values, tf_vectors)
    """
    logger.debug(f"Computing TF-IDF for {len(documents)} documents")
    # Tokenize all documents
    tokenized_docs = [tokenize_text(doc) for doc in documents]

    # Build vocabulary
    vocabulary = {}
    word_to_idx = {}
    idx = 0
    for tokens in tokenized_docs:
        for token in set(tokens):  # Use set to avoid double counting in same doc
            if token not in word_to_idx:
                word_to_idx[token] = idx
                vocabulary[idx] = token
                idx += 1

    # Compute term frequency (TF) for each document
    tf_vectors = []
    for tokens in tokenized_docs:
        tf = Counter(tokens)
        # Normalize by document length
        vec = [0.0] * len(vocabulary)
        for token, count in tf.items():
            if token in word_to_idx:
                vec[word_to_idx[token]] = count / len(tokens)
        tf_vectors.append(vec)

    # Compute inverse document frequency (IDF)
    num_docs = len(tokenized_docs)
    idf = [0.0] * len(vocabulary)
    for idx in range(len(vocabulary)):
        # Count documents containing this term
        df = sum(1 for tokens in tokenized_docs if vocabulary[idx] in set(tokens))
        idf[idx] = math.log(num_docs / (df + 1)) + 1  # Add 1 to avoid division by zero

    logger.debug(f"TF-IDF computation complete. Vocabulary size: {len(vocabulary)}")
    return vocabulary, idf, tf_vectors

def compute_tf_idf_query(query, vocabulary, idf):
    """Compute TF-IDF vector for a query using existing vocabulary and IDF."""
    tokens = tokenize_text(query)
    tf = Counter(tokens)
    vec = [0.0] * len(vocabulary)
    for token, count in tf.items():
        if token in vocabulary.values():  # Check if token is in vocabulary
            # Find index of token
            token_idx = None
            for idx, vocab_token in vocabulary.items():
                if vocab_token == token:
                    token_idx = idx
                    break
            if token_idx is not None:
                vec[token_idx] = (count / len(tokens)) * idf[token_idx]
    return vec

def hybrid_search_score(vector_score, keyword_score, alpha=0.7):
    """
    Combine vector and keyword scores using weighted average.
    alpha: weight for vector score (1-alpha for keyword score)
    """
    return alpha * vector_score + (1 - alpha) * keyword_score

## -- Carga del CAG -- ##

def cargar_cag(rutas, client, modelo):
    """
    Lee las plantillas locales, construye el prompt del sistema y
    crea un Context Cache real en los servidores de Google (CAG).
    """
    logger.info("Loading CAG (Context Augmented Generation)")
    contexto_local = ""
    for ruta in rutas:
        if os.path.exists(ruta):
            with open(ruta, 'r', encoding='utf-8') as f:
                contenido = f.read()
                contexto_local += f"\n--- PLANTILLA: {os.path.basename(ruta)} ---\n{contenido}\n"
                logger.debug(f"Loaded template: {os.path.basename(ruta)} ({len(contenido)} chars)")
        else:
            logger.warning(f"Template not found: {os.path.basename(ruta)}")
            print(f"  [WARN] Plantilla no encontrada: {os.path.basename(ruta)}")

    if not contexto_local.strip():
        logger.error("No CAG templates found")
        raise RuntimeError("Error: No se encontró ninguna plantilla base para el CAG.")

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(contexto_cag=contexto_local)
    logger.debug(f"System prompt created ({len(system_prompt)} chars)")

    logger.info("Uploading static context (CAG) to Google API")
    cache = client.create_cached_content(
        model=modelo,
        config=types.CreateCachedContentConfig(
            system_instruction=system_prompt,
            contents=[
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text="Inicializando contexto CAG base.")]
                )
            ],
            ttl="3600s"
        )
    )
    logger.info(f"CAG cache created successfully: {cache.name}")
    print(f"  [✓] Caché creada con éxito en la nube: {cache.name}")

    return cache

## -- Funciones para RAG -- ##

def cargar_bd(ruta_local):
    if os.path.exists(ruta_local):
        logger.info(f"Loading vector database from '{ruta_local}'")
        print(f"  -> Cargando BD vectorial desde '{ruta_local}'...")
        with open(ruta_local, 'rb') as f:
            return pickle.load(f)
    logger.info("No existing vector database found, creating new one")
    return []

def guardar_bd(bd, ruta_local):
    logger.debug(f"Saving vector database to '{ruta_local}' with {len(bd)} entries")
    with open(ruta_local, 'wb') as f:
        pickle.dump(bd, f)

def extraer_documentos(rutas):
    logger.info(f"Extracting documents from {len(rutas)} paths")
    docs = []
    for ruta in rutas:
        if not os.path.exists(ruta):
            logger.warning(f"RAG path not found: {os.path.basename(ruta)}")
            print(f"  [WARN] RAG no encontrado: {os.path.basename(ruta)}")
            continue
        try:
            if ruta.lower().endswith('.pdf'):
                logger.info(f"Processing PDF: {os.path.basename(ruta)}")
                # Try to use pdfplumber for better table extraction if available
                if HAS_PDFPLUMBER:
                    try:
                        with pdfplumber.open(ruta) as pdf:
                            for n, pagina in enumerate(pdf.pages):
                                # Extract text
                                texto = pagina.extract_text() or ""

                                # Extract tables and convert to text
                                tablas = pagina.extract_tables()
                                texto_tablas = ""
                                for i, tabla in enumerate(tablas):
                                    texto_tablas += f"\n\nTabla {i+1} en página {n+1}:\n"
                                    for fila in tabla:
                                        # Clean None values and join with spaces
                                        fila_limpia = [str(celda) if celda is not None else "" for celda in fila]
                                        texto_tablas += " | ".join(fila_limpia) + "\n"

                                # Combine text and tables
                                texto_completo = texto
                                if texto_tablas.strip():
                                    texto_completo += "\n\n=== TABLAS EXTRAÍDAS ===" + texto_tablas

                                if texto_completo.strip():
                                    # chunking fino por página
                                    nombre = f"{os.path.basename(ruta)}_p{n+1}"
                                    chunks = chunk_texto(texto_completo, nombre)
                                    docs.extend(chunks)
                                    logger.debug(f"Page {n+1}: {len(chunks)} chunks extracted (text + {len(tablas)} tables)")
                    except Exception as e:
                        logger.warning(f"pdfplumber failed for {os.path.basename(ruta)}, falling back to PyPDF2: {e}")
                        # Fall back to PyPDF2
                        with open(ruta, 'rb') as f:
                            lector = PyPDF2.PdfReader(f)
                            for n, pagina in enumerate(lector.pages):
                                texto = pagina.extract_text() or ""
                                if texto.strip():
                                    # chunking fino por página
                                    nombre = f"{os.path.basename(ruta)}_p{n+1}"
                                    docs.extend(chunk_texto(texto, nombre))
                                    logger.debug(f"Page {n+1}: {len(chunk_texto(texto, nombre))} chunks extracted")
                else:
                    # Use PyPDF2 only
                    with open(ruta, 'rb') as f:
                        lector = PyPDF2.PdfReader(f)
                        for n, pagina in enumerate(lector.pages):
                            texto = pagina.extract_text() or ""
                            if texto.strip():
                                # chunking fino por página
                                nombre = f"{os.path.basename(ruta)}_p{n+1}"
                                docs.extend(chunk_texto(texto, nombre))
                                logger.debug(f"Page {n+1}: {len(chunk_texto(texto, nombre))} chunks extracted")
            else:
                logger.info(f"Processing text file: {os.path.basename(ruta)}")
                with open(ruta, 'r', encoding='utf-8') as f:
                    texto = f.read()
                if texto.strip():
                    docs.extend(chunk_texto(texto, os.path.basename(ruta)))
                    logger.debug(f"Text file: {len(chunk_texto(texto, os.path.basename(ruta)))} chunks extracted")
        except Exception as e:
            logger.error(f"Error reading {os.path.basename(ruta)}: {e}")
            print(f"  [ERROR] Leyendo {os.path.basename(ruta)}: {e}")
    logger.info(f"Document extraction complete: {len(docs)} total chunks")
    return docs

def vectorizar_pendientes(bd, docs_extraidos, client):
    ya_procesados = {d["nombre"] for d in bd}
    pendientes = [d for d in docs_extraidos if d["nombre"] not in ya_procesados]
    total = len(pendientes)
    if total == 0:
        logger.info("No new documents to vectorize")
        return bd

    logger.info(f"Vectorizing {total} new document chunks")
    print(f"\n[3/4] Vectorizando {total} chunks nuevos...")
    for i, doc in enumerate(pendientes):
        exito, intentos = False, 0
        while not exito and intentos < 5:
            try:
                logger.debug(f"Vectorizing chunk: {doc['nombre']}")
                # Use the client's embed_content method (works for any LLMProvider)
                resp = client.embed_content(
                    model=configuraciones.MODEL_EMB,
                    contents=doc["texto"]
                )
                # Para búsqueda híbrida, también calculamos el vector TF-IDF
                # Pero lo almacenaremos de forma separada por ahora
                bd.append({
                    "nombre": doc["nombre"],
                    "texto":  doc["texto"],
                    "vector": resp.embeddings[0].values,
                })
                exito = True
                logger.info(f"Vectorized chunk {i+1}/{total}: {doc['nombre']}")
                print(f"  [{i+1}/{total}] {doc['nombre']}")
                if (i + 1) % 10 == 0 or (i + 1) == total:
                    guardar_bd(bd, configuraciones.BD_LOCAL)
                    logger.info(f"Checkpoint saved: {(i+1)*10 if (i+1)%10==0 else total} vectors")
                    print("  [✓] Checkpoint guardado.")
            except Exception as e:
                if "429" in str(e):
                    intentos += 1
                    espera = 60 * intentos
                    logger.warning(f"API rate limit hit, waiting {espera}s (attempt {intentos}/5)")
                    print(f"  [429] Límite API. Pausando {espera}s (intento {intentos}/5)...")
                    time.sleep(espera)
                else:
                    logger.error(f"Vectorization error for {doc['nombre']}: {e}")
                    print(f"  [ERROR] Vectorización: {e}")
                    break
        if not exito:
            logger.error(f"Failed to vectorize {doc['nombre']} after 5 attempts")
            guardar_bd(bd, configuraciones.BD_LOCAL)
            raise RuntimeError(
                f"API bloqueada tras 5 intentos en '{doc['nombre']}'. "
                "Progreso guardado. Reinicia el script más tarde."
            )
    logger.info(f"Vectorization complete: {len(bd)} total vectors in database")
    return bd

## -- Busqueda RAG -- ##

def buscar_rag(pregunta, bd, client, top_k=configuraciones.TOP_K):
    """
    Búsqueda híbrida que combina vectores semánticos y TF-IDF
    """
    logger.info(f"Performing hybrid search for query: '{pregunta[:50]}...' ({len(pregunta)} chars)")

    # Búsqueda vectorial existente
    logger.debug("Computing query embedding")
    # Use the client's embed_content method (works for any LLMProvider)
    emb = client.embed_content(
        model=configuraciones.MODEL_EMB,
        contents=pregunta
    ).embeddings[0].values

    vector_scores = []
    for doc in bd:
        score = sim_cos(emb, doc["vector"])
        vector_scores.append(score)

    # Búsqueda por TF-IDF (palabra clave)
    # Extraer todos los textos para crear el índice TF-IDF si no existe
    # Para simplificar, vamos a calcular TF-IDF en tiempo real para la consulta
    # y comparar con los documentos usando una aproximación

    logger.debug("Computing TF-IDF scores for keyword matching")
    keyword_scores = []
    query_tokens = set(tokenize_text(pregunta))
    logger.debug(f"Query tokens: {list(query_tokens)[:10]}")  # First 10 tokens

    for i, doc in enumerate(bd):
        doc_tokens = set(tokenize_text(doc["texto"]))
        # Simple Jaccard similarity for keyword matching
        if len(query_tokens) == 0 and len(doc_tokens) == 0:
            keyword_score = 0.0
        elif len(query_tokens) == 0 or len(doc_tokens) == 0:
            keyword_score = 0.0
        else:
            intersection = len(query_tokens.intersection(doc_tokens))
            union = len(query_tokens.union(doc_tokens))
            keyword_score = intersection / union if union > 0 else 0.0
        keyword_scores.append(keyword_score)

    # Combinar scores usando búsqueda híbrida
    logger.debug("Combining vector and keyword scores")
    combined_scores = []
    for i in range(len(bd)):
        combined = hybrid_search_score(vector_scores[i], keyword_scores[i])
        combined_scores.append(combined)

    # Obtener los top_k resultados basado en el score combinado
    logger.debug(f"Top {top_k} vector scores: {sorted(vector_scores, reverse=True)[:top_k]}")
    logger.debug(f"Top {top_k} keyword scores: {sorted(keyword_scores, reverse=True)[:top_k]}")
    logger.debug(f"Top {top_k} combined scores: {sorted(combined_scores, reverse=True)[:top_k]}")

    ranked_indices = sorted(range(len(combined_scores)), key=lambda i: combined_scores[i], reverse=True)
    ranked_bd = [bd[i] for i in ranked_indices[:top_k]]

    logger.info(f"Hybrid search complete: returned {len(ranked_bd)} results")
    return ranked_bd